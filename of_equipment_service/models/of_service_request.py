# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class OFServiceRequest(models.Model):
    _inherit = 'of.service.request'

    # Equipment
    use_equipment = fields.Boolean(string="Use Equipments")
    equipment_ids = fields.Many2many(
        comodel_name='of.equipment',
        relation='of_service_request_equipment_rel',
        column1='request_id',
        column2='equipment_id',
        string="Equipments",
        compute='_compute_equipment_ids',
        store=True,
        readonly=False,
        domain="[('customer_id', '=', partner_id), '|', ('site_address_id', '=', address_id), "
        "('customer_id', '=', address_id)]",
    )
    equipment_intervention_ids = fields.One2many(
        comodel_name='of.service.request.equipment.line',
        inverse_name='request_id',
        string="Equipment Interventions",
        readonly=True,
    )

    # Payer
    payer_mode = fields.Selection(
        selection=[
            ('customer', "Customer"),
            ('reseller', "Reseller"),
            ('manufacturer', "Manufacturer"),
        ],
        string="Payer",
    )

    # Date and time
    service_start = fields.Datetime(copy=False)
    service_stop = fields.Datetime(copy=False)
    response_time = fields.Float(
        string="Response time (hours)", compute='_compute_response_time', store=True, group_operator='avg'
    )
    service_time = fields.Float(
        string="Service time (hours)", compute='_compute_service_time', store=True, group_operator='avg'
    )

    # --------------------------------------------------
    # Constraints
    # --------------------------------------------------

    @api.constrains('equipment_ids')
    def _check_equipment_ids(self):
        if self._context.get('ignore_equipment_ids_check'):
            return
        for request in self:
            if request.use_equipment:
                if len(request.equipment_ids) > 1:
                    raise ValidationError(_("Please add only one equipment."))
                elif len(request.equipment_ids) == 0:
                    raise ValidationError(_("Please add at least one equipment."))

    # --------------------------------------------------
    # Compute methods
    # --------------------------------------------------

    def _search_equipment_id(self, operator, value):
        return [('id', operator, value)]

    @api.depends('equipment_ids.intervention_ids')
    def _compute_history_intervention_ids(self):
        """Compute the history interventions for the service request. Used in form view and Sheet/Report reports."""
        request_with_equipments = self.filtered(lambda r: r.equipment_ids)
        for request in request_with_equipments:
            request.history_intervention_ids = request.mapped('equipment_ids.intervention_ids')
        super(OFServiceRequest, self - request_with_equipments)._compute_history_intervention_ids()

    @api.depends('create_date', 'service_start')
    def _compute_response_time(self):
        for request in self:
            if request.create_date and request.service_start:
                duration = request.service_start - request.create_date
                request.response_time = duration.total_seconds() / 3600.0
            else:
                request.response_time = 0.0

    @api.depends('create_date', 'service_stop')
    def _compute_service_time(self):
        for request in self:
            if request.create_date and request.service_stop:
                duration = request.service_stop - request.create_date
                request.service_time = duration.total_seconds() / 3600.0
            else:
                request.service_time = 0.0

    @api.depends('use_equipment', 'address_id', 'partner_id')
    def _compute_equipment_ids(self):
        equipment_obj = self.env['of.equipment']
        for request in self:
            if request.address_id and request.use_equipment:
                equipment = equipment_obj.search(
                    [('site_address_id', '=', request.address_id.id)], limit=1
                ) or equipment_obj.search([('customer_id', '=', request.address_id.id)], limit=1)
                if not equipment and request.partner_id:
                    equipment = equipment_obj.search([('customer_id', '=', request.partner_id.id)], limit=1)
                if equipment:
                    request.equipment_ids = equipment

    # --------------------------------------------------
    # ORM methods
    # --------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        requests_with_equipment = requests.filtered(lambda r: r.use_equipment)
        requests_with_equipment and requests_with_equipment._populate_service_request_equipment_line()
        return requests

    def write(self, vals):
        if 'equipment_ids' in vals:
            equipments_by_request = {request.id: request.equipment_ids.ids for request in self}
        res = super().write(vals)
        if vals.get('use_equipment'):
            self._populate_service_request_equipment_line()
        if 'use_equipment' in vals and not vals['use_equipment']:
            self.equipment_intervention_ids and self.equipment_intervention_ids.unlink()
        if 'equipment_ids' in vals:
            requests_to_updates = self.env['of.service.request'].browse(
                [
                    request_id
                    for request_id, equipment_ids in equipments_by_request.items()
                    if equipment_ids != vals['equipment_ids'][0][2]
                ]
            )
            requests_to_updates._populate_service_request_equipment_line()
            requests_to_updates._unlink_service_request_equipment_line()
            # TODO: Should we unlink equipment on linked interventions? Or should we keep them and just unlink the
            # equipment intervention lines?
            # Also maybe just forbid to unlink equipment if there are linked interventions ?
        if vals.get('stage_id'):
            stage = self.env['of.service.request.stage'].browse(vals.get('stage_id'))
            if stage and stage.state == 'open':
                for request in self.filtered(lambda r: not r.service_start):
                    request.service_start = fields.Datetime.now()
            if stage and stage.state == 'done':
                for request in self.filtered(lambda r: not r.service_stop):
                    request.service_stop = fields.Datetime.now()
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        res = super()._read_group_stage_ids(stages, domain, order)
        if self._context.get('of_kanban_steps') == "After-Sales Service":
            if after_sales_type := self.env.ref(
                'of_equipment_service.of_service_request_type_after_sales',
                raise_if_not_found=False,
            ):
                return res.filtered(lambda r: after_sales_type.id in r.type_ids.ids)
        return res

    # --------------------------------------------------
    # Business methods
    # --------------------------------------------------

    def _get_action_view_intervention_context(self, context=None):
        if context is None:
            context = {}

        context = super()._get_action_view_intervention_context(context)
        context['default_use_equipment'] = self.equipment_ids and self.equipment_ids.ids or False
        context['default_equipment_ids'] = [Command.set(self.equipment_ids and self.equipment_ids.ids or [])]
        return context

    def _populate_service_request_equipment_line(self):
        """Populate the equipment intervention lines of the service request.
        That will check if the equipment intervention lines already exists and create them if not.
        """
        values_list = []
        for request in self:
            current_values = request.equipment_intervention_ids.mapped(
                lambda line: (line.request_id.id, line.equipment_id.id, line.event_id.id)
            )
            for intervention in request.intervention_ids:
                intervention_equipments = intervention.of_equipment_ids.filtered(lambda e: e in request.equipment_ids)
                values_list.extend(
                    {
                        'request_id': request.id,
                        'equipment_id': equipment.id,
                        'event_id': intervention.id,
                        'start': intervention.start,
                    }
                    for equipment in intervention_equipments
                    if (request.id, equipment.id, intervention.id) not in current_values
                )
        values_list and self.env['of.service.request.equipment.line'].create(values_list)

    def _unlink_service_request_equipment_line(self, requests_data=None):
        """Unlink the equipment intervention lines of the service request.
        That will check if the equipment intervention lines are still linked to the request and unlink them if not.
        If requests_data is provided, thats because we are modifying the equipment_ids of the intervention and we need
        to remove the equipment intervention lines that are not linked to the request anymore.

        :param requests_data: A dictionary containing the equipment ids removed by event for each request.
        """
        for request in self:
            # Remove equipment intervention lines if the equipment or the intervention are not linked to the
            # request anymore
            equipment_intervention_to_unlink = request.equipment_intervention_ids.filtered(
                lambda line: line.event_id.id not in request.intervention_ids.ids
                or line.equipment_id.id not in request.equipment_ids.ids
            )
            equipment_intervention_to_unlink and equipment_intervention_to_unlink.unlink()
        # Remove equipment intervention lines if the equipment is not linked to an intervention of the
        # request anymore
        if requests_data:
            for request, equipments_removed_by_event in requests_data.items():
                for event, equipment_ids in equipments_removed_by_event.items():
                    request.equipment_intervention_ids.filtered(
                        lambda line: line.event_id.id == event.id and line.equipment_id.id in equipment_ids
                    ).unlink()
