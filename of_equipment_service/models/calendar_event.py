# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    of_equipment_ids_domain = fields.Many2many(
        comodel_name='of.equipment',
        compute='_compute_equipment_ids_domain',
        help="Technical field to compute domain for equipment_ids field based on the related service request",
    )
    of_equipment_ids = fields.Many2many(
        domain="[('id', 'in', of_equipment_ids_domain and of_equipment_ids_domain or [])]",
        compute=False,  # Disable compute, because now equipments are managed by the service request if
        # the event is linked to one
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('of_request_id', 'of_partner_id', 'of_address_id')
    def _compute_equipment_ids_domain(self):
        """Compute the domain for the equipment_ids field based on the related service request and partner/address.
        We need to filter equipments that are already linked to the service request if there is one, otherwise we filter
        equipments based on the partner and address of the event.
        """
        for event in self:
            if event.of_request_id:
                already_linked_equipment_ids = event.of_request_id.mapped('equipment_intervention_ids.equipment_id.id')
                request_equipments = event.of_request_id.equipment_ids.filtered(
                    lambda e: e.id not in already_linked_equipment_ids
                )
                event.of_equipment_ids_domain = request_equipments.ids
            else:
                event.of_equipment_ids_domain = (
                    self.env['of.equipment']
                    .search(
                        [
                            '|',
                            '|',
                            ('customer_id', '=', event.of_partner_id.id),
                            ('customer_id', '=', event.of_address_id.id),
                            ('site_address_id', '=', event.of_address_id.id),
                        ]
                    )
                    .ids
                )

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        request_obj = self.env['of.service.request']
        for vals in vals_list:
            if vals.get('of_use_equipment'):
                request = vals.get('of_request_id') and request_obj.browse(vals['of_request_id'])
                if request and not vals.get('of_equipment_ids'):
                    equipments = request.equipment_ids
                    vals['of_equipment_ids'] = [Command.set(equipments.ids)]

        events = super().create(vals_list)

        requests_to_populate = request_obj.browse(
            [
                event.of_request_id.id
                for event, vals in zip(events, vals_list)
                if vals.get('of_use_equipment') and event.of_type == 'intervention' and event.of_request_id
            ]
        )
        # Populate service request equipment lines for events created with a service request and equipment
        requests_to_populate and requests_to_populate._populate_service_request_equipment_line()
        return events

    def write(self, vals):
        event_intervention = self.filtered(lambda e: e.of_type == 'intervention')
        if 'of_request_id' in vals:
            request_by_event = {event: event.of_request_id for event in event_intervention if event.of_request_id}
        if 'of_equipment_ids' in vals:
            equipments_by_event = {
                event: event.of_equipment_ids.ids for event in event_intervention if event.of_equipment_ids
            }

        res = super().write(vals)

        # Handle changes on service request equipment lines
        if 'of_request_id' in vals:
            self._handle_request_changes(request_by_event, vals)
        if 'of_equipment_ids' in vals:
            self._handle_equipments_change(equipments_by_event, vals)
        return res

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _handle_request_changes(self, request_by_event, vals):
        """Apply changes on service request equipment lines when a service request is modified or removed.

        :param request_by_event: dictionary of events and their related service request before the changes
        :type request_by_event: dict
        :param vals: dictionary of values to write on the events
        :type vals: dict
        """
        if 'of_request_id' in vals and not vals['of_request_id']:
            # Events for which has been removed the service request, we need to remove the equipment lines
            events_with_request = self.filtered(lambda e: e in request_by_event and not e.of_request_id)
            requests_to_remove = self.env['of.service.request'].browse(
                [request_by_event[event].id for event in events_with_request]
            )
            requests_to_remove._unlink_service_request_equipment_line()

        if 'of_request_id' in vals and vals['of_request_id']:
            # Events for which has been modified the service request, we need to remove the equipment lines from the
            # previous linked service request
            events_with_modified_request = self.filtered(
                lambda e: e in request_by_event and e.of_request_id != request_by_event[e]
            )
            requests_to_remove = self.env['of.service.request'].browse(
                [request_by_event[event].id for event in events_with_modified_request]
            )
            requests_to_remove._unlink_service_request_equipment_line()

            # Events for which has been set a new service request or changed the service request, we need to add the
            # equipment lines to the new linked service request
            events_with_new_request = self.filtered(
                lambda e: e not in request_by_event or e.of_request_id != request_by_event[e]
            )
            events_with_new_request.mapped('of_request_id')._populate_service_request_equipment_line()

    def _handle_equipments_change(self, equipments_by_event, vals):
        """Apply changes on service request equipment lines when the equipment of an event is modified.

        :param equipments_by_event: dictionary of events and their related equipment before the changes
        :type equipments_by_event: dict
        :param vals: dictionary of values to write on the events
        :type vals: dict
        """
        if 'of_equipment_ids' in vals and (not vals['of_equipment_ids'] or not vals['of_equipment_ids'][0][2]):
            # Events for which has been removed all equipments, we need to remove the equipment lines from
            # linked service request
            events_with_request = self.filtered(lambda e: e in equipments_by_event and not e.of_equipment_ids)
            events_with_request.mapped('of_request_id')._unlink_service_request_equipment_line()

        if 'of_equipment_ids' in vals and vals['of_equipment_ids'] and vals['of_equipment_ids'][0][2]:
            # Events for which has been modified equipments, we need to remove the equipment lines from the
            # service request for equipments that are not in the new list
            events_with_modified_equipments = self.filtered(
                lambda e: e in equipments_by_event and e.of_equipment_ids.ids != equipments_by_event[e]
            )
            requests_data = {
                event.of_request_id: {event: list(set(equipments_by_event[event]) - set(event.of_equipment_ids.ids))}
                for event in events_with_modified_equipments
            }
            events_with_modified_equipments.mapped('of_request_id')._unlink_service_request_equipment_line(
                requests_data
            )

            # Events for which has been set a new equipments list or changed it, we need to add the
            # equipment lines to linked service request
            events_with_new_equipments = self.filtered(
                lambda e: e not in equipments_by_event or e.of_equipment_ids.ids != equipments_by_event[e]
            )
            events_with_new_equipments.mapped('of_request_id')._populate_service_request_equipment_line()
