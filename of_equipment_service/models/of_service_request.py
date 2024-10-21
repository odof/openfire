# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

from .tools import _get_values_diff


class OFServiceRequest(models.Model):
    _inherit = "of.service.request"

    # Equipment
    use_equipment = fields.Boolean(
        string="Use Equipments",
        help="Activate this field to add one or more items of equipment to be worked on.",
    )
    linked_equipment_ids = fields.One2many(
        comodel_name="of.service.request.equipment.link",
        inverse_name="service_request_id",
        string="Linked Equipments",
        compute="_compute_linked_equipment_ids",
        store=True,
        readonly=False,
        copy=False,
    )
    equipment_ids = fields.Many2many(
        comodel_name="of.equipment",
        relation="of_service_request_equipment_rel",
        column1="request_id",
        column2="equipment_id",
        string="Equipments",
        compute="_compute_equipment_ids",
        store=True,
        readonly=False,
        copy=False,
        help="Technical field to store the equipment linked to the service request, to easier access them.",
    )
    equipment_intervention_ids = fields.One2many(
        comodel_name="of.service.request.equipment.line",
        inverse_name="request_id",
        string="Equipment Interventions",
        readonly=True,
    )

    # Payer
    payer_mode = fields.Selection(
        selection=[
            ("customer", "Customer"),
            ("reseller", "Reseller"),
            ("manufacturer", "Manufacturer"),
        ],
        string="Payer",
    )

    # Date and time
    service_start = fields.Datetime(copy=False)
    service_stop = fields.Datetime(copy=False)
    response_time = fields.Float(
        string="Response time (hours)", compute="_compute_response_time", store=True, group_operator="avg"
    )
    service_time = fields.Float(
        string="Service time (hours)", compute="_compute_service_time", store=True, group_operator="avg"
    )

    # Misc fields
    default_equipment_report_tmpl_id = fields.Many2one(
        related="template_id.default_equipment_report_tmpl_id",
        string="Default Equipment Report Template",
        help="Technical field to get the default equipment report from the intervention template.",
    )

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    def _search_equipment_id(self, operator, value):
        return [("id", operator, value)]

    @api.depends("equipment_ids.intervention_ids")
    def _compute_history_intervention_ids(self):
        """Compute the history interventions for the service request. Used in form view and Sheet/Report reports."""
        request_with_equipments = self.filtered(lambda r: r.equipment_ids)
        for request in request_with_equipments:
            request.history_intervention_ids = request.mapped("equipment_ids.intervention_ids")
        super(OFServiceRequest, self - request_with_equipments)._compute_history_intervention_ids()

    @api.depends("create_date", "service_start")
    def _compute_response_time(self):
        for request in self:
            if request.create_date and request.service_start:
                duration = request.service_start - request.create_date
                request.response_time = duration.total_seconds() / 3600.0
            else:
                request.response_time = 0.0

    @api.depends("create_date", "service_stop")
    def _compute_service_time(self):
        for request in self:
            if request.create_date and request.service_stop:
                duration = request.service_stop - request.create_date
                request.service_time = duration.total_seconds() / 3600.0
            else:
                request.service_time = 0.0

    @api.depends("use_equipment", "address_id", "partner_id")
    def _compute_linked_equipment_ids(self):
        equipment_obj = self.env["of.equipment"]
        requests_use_equipment = self.filtered("use_equipment")
        for request in requests_use_equipment:
            equipments = equipment_obj.search(
                [("site_address_id", "=", request.address_id.id)]
            ) or equipment_obj.search([("customer_id", "=", request.address_id.id)])
            if not equipments and request.partner_id:
                equipments = equipment_obj.search([("customer_id", "=", request.partner_id.id)])

            request.linked_equipment_ids = (
                [
                    Command.create(
                        request._prepare_service_request_equipment_link_values_from_equipment(equipment=equipment)
                    )
                    for equipment in equipments
                ]
                if len(equipments) == 1
                else False
            )

        for request in self - requests_use_equipment:
            request.linked_equipment_ids = False

    @api.depends("linked_equipment_ids", "linked_equipment_ids.equipment_id")
    def _compute_equipment_ids(self):
        requests_with_equipment = self.filtered("linked_equipment_ids")
        for request in requests_with_equipment:
            request.equipment_ids = request.linked_equipment_ids.mapped("equipment_id")
        for request in self - requests_with_equipment:
            request.equipment_ids = False

    @api.depends("task_id", "linked_equipment_ids", "linked_equipment_ids.task_id")
    def _compute_duration(self):
        requests_with_equipment = self.filtered(lambda r: r.linked_equipment_ids)
        for request in requests_with_equipment:
            if all(line.task_id for line in request.linked_equipment_ids):
                request.duration = sum(link.task_duration for link in request.linked_equipment_ids)
            else:
                line_without_task = request.linked_equipment_ids.filtered(lambda line: not line.task_id)
                line_with_task = request.linked_equipment_ids.filtered(lambda line: line.task_id)
                duration_with_task = sum(line_with_task.mapped("task_duration"))
                request.duration = (request.task_id.duration * len(line_without_task)) + duration_with_task

            # Fall back to the task duration if the request duration is still not set
            if not request.duration and request.task_id.duration:
                request.duration = request.task_id.duration

        for request in self - requests_with_equipment:
            if request.task_id and not request.duration:
                request.duration = request.task_id.duration

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        requests_with_equipment = requests.filtered(lambda r: r.use_equipment)
        requests_with_equipment and requests_with_equipment._populate_service_request_equipment_line()
        return requests

    def write(self, vals):
        self._check_raise_removed_equipment_links(vals)

        if "linked_equipment_ids" in vals or "of_use_equipment" in vals:
            saved_equipment_links_by_request = {
                request: {
                    link: {
                        "equipment_id": link.equipment_id.id,
                        "task_id": link.task_id.id,
                        "equipment_report_tmpl_id": link.equipment_report_tmpl_id.id,
                    }
                    for link in request.linked_equipment_ids
                }
                for request in self
                if request.linked_equipment_ids
            }

        res = super().write(vals)

        if "linked_equipment_ids" in vals:
            self._handle_equipments_change(saved_equipment_links_by_request)

        if vals.get("stage_id"):
            stage = self.env["of.service.request.stage"].browse(vals.get("stage_id"))
            if stage and stage.state == "open":
                for request in self.filtered(lambda r: not r.service_start):
                    request.service_start = fields.Datetime.now()
            if stage and stage.state == "done":
                for request in self.filtered(lambda r: not r.service_stop):
                    request.service_stop = fields.Datetime.now()
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        res = super()._read_group_stage_ids(stages, domain, order)
        if self._context.get("of_kanban_steps") == "After-Sales Service":
            if after_sales_type := self.env.ref(
                "of_equipment_service.of_service_request_type_after_sales",
                raise_if_not_found=False,
            ):
                return res.filtered(lambda r: after_sales_type.id in r.type_ids.ids)
        return res

    # --------------------------------------------------------------------------
    # Action methods
    # --------------------------------------------------------------------------

    def action_button_add_equipments_to_sr(self):
        self.ensure_one()
        context = self.env.context.copy()
        context["default_service_request_id"] = self.id
        view = self.env.ref("of_equipment_service.of_equipment_link_create_form_view")
        return {
            "name": _("Add Equipment to Service Request"),
            "res_model": "of.equipment.link.create.wizard",
            "view_mode": "form",
            "view_id": view.id,
            "context": context,
            "target": "new",
            "type": "ir.actions.act_window",
        }

    def action_button_remove_all_equipments(self):
        self.ensure_one()
        self.linked_equipment_ids.unlink()
        return True

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _check_raise_removed_equipment_links(self, vals):
        """
        Checks if there are any equipment links that are being removed and raises an error if they are linked to any
        interventions.

        Args:
            vals (dict): A dictionary of values being updated on the service request.

        Raises:
            UserError: If any equipment links being removed are associated with interventions.
        """
        raise_message = False
        events_data = []
        if "linked_equipment_ids" in vals:
            removed_equipment_links = self.env["of.service.request.equipment.link"].browse(
                [link[1] for link in vals["linked_equipment_ids"] if link[0] in (Command.DELETE, Command.UNLINK)]
            )
            for link in removed_equipment_links:
                if events := link.service_request_id.intervention_ids.filtered(
                    lambda e: link in e.of_linked_equipment_ids.mapped("request_link_id")
                ):
                    raise_message = True
                    for event in events:
                        if (event.id, event.name) not in events_data:
                            events_data.append((event.id, event.name))

        if (
            "use_equipment" in vals
            and not vals["use_equipment"]
            and any(request.equipment_intervention_ids for request in self)
        ):
            raise_message = True
            for request in self:
                for event in request.intervention_ids:
                    if (event.id, event.name) not in events_data:
                        events_data.append((event.id, event.name))

        if raise_message:
            events_message = "\n".join([f"- {ev_name} (id: {ev_id})" for ev_id, ev_name in events_data])
            events_message = (
                _("\n\nLinked interventions:\n%(events_message)s", events_message=events_message) if events_data else ""
            )
            raise UserError(
                _(
                    "You cannot delete equipment linked to one or more interventions.\n"
                    "Please delete the equipment(s) for the concerned intervention(s).%(events_message)s",
                    events_message=events_message,
                )
            )

    def _get_action_view_intervention_context(self, context=None):
        if context is None:
            context = {}

        context = super()._get_action_view_intervention_context(context)
        context["default_of_use_equipment"] = self.equipment_ids and self.equipment_ids.ids or False
        context["default_of_linked_equipment_ids"] = [
            Command.create(
                {
                    "equipment_id": link.equipment_id.id,
                    "task_id": link.task_id.id,
                    "equipment_report_tmpl_id": link.equipment_report_tmpl_id.id,
                }
            )
            for link in self.linked_equipment_ids
        ]

        return context

    def _handle_equipments_change(self, saved_equipment_links_by_request):
        """
        Handles changes in equipment links for service requests.

        This method performs the following actions:
        * Updates existing event equipment links based on the changes in the equipment links of the service requests.
            As we updated equipment links on the service request, we need to ensure that the corresponding event
                equipment links are updated as well.
        * Updates the equipment lines in service requests based on the provided data.
        """
        updated_links = []
        for request, equipment_links_data in saved_equipment_links_by_request.items():
            updated_links.extend(
                {"link": link, "old_values": equipment_links_data[link]}
                for link in request.linked_equipment_ids
                if (
                    link in equipment_links_data
                    and (
                        link.equipment_id.id != equipment_links_data[link]["equipment_id"]
                        or link.task_id.id != equipment_links_data[link]["task_id"]
                        or link.equipment_report_tmpl_id.id != equipment_links_data[link]["equipment_report_tmpl_id"]
                    )
                )
            )

        if updated_links:
            request_data = {}  # {request_id: {event_id: {link_id: {old_equipment_id, new_equipment_id}}}}
            for data in updated_links:  # [{"link": link, "old_values": old_values}, ...]
                request_equipment_lnk = data["link"]
                if event_equipment_lnk := request_equipment_lnk.service_request_id.mapped(
                    "intervention_ids.of_linked_equipment_ids"
                ).filtered(lambda event_lnk: event_lnk.request_link_id.id == request_equipment_lnk.id):
                    request_data.setdefault(request_equipment_lnk.service_request_id, {}).setdefault(
                        event_equipment_lnk.event_id, {}
                    )[event_equipment_lnk.id] = {
                        "old_equipment_id": data["old_values"]["equipment_id"],
                        "new_equipment_id": request_equipment_lnk.equipment_id.id,
                    }
                    # Write the diff on the event equipment link
                    new_values = _get_values_diff(
                        data["old_values"],
                        {
                            "equipment_id": request_equipment_lnk.equipment_id.id,
                            "task_id": request_equipment_lnk.task_id.id,
                            "equipment_report_tmpl_id": request_equipment_lnk.equipment_report_tmpl_id.id,
                        },
                    )
                    event_equipment_lnk.write(new_values)
                    # Post a message on the event and the service request to inform about the change
                    request_equipment_lnk._post_self_update_message(data["old_values"], new_values)
                    event_equipment_lnk._post_event_message(
                        request_equipment_lnk.service_request_id, data["old_values"], new_values
                    )

            # Keep the equipment lines updated for the requests
            self._update_service_request_equipment_line(request_data)

    def _populate_service_request_equipment_line(self):
        """Populate the equipment intervention lines of the service request.
        That will check if the equipment intervention lines already exists and create them if not.
        """
        values_list = []
        for request in self:
            # Get current values to avoid creating duplicates
            current_values = request.equipment_intervention_ids.mapped(
                lambda line: (line.request_id.id, line.equipment_id.id, line.event_id.id, line.event_link_id.id)
            )
            for intervention in request.intervention_ids:
                # Get the equipment intervention lines of the intervention that are linked to the request
                event_equipment_links = intervention.of_linked_equipment_ids.filtered(
                    lambda lnk: lnk.equipment_id in request.equipment_ids
                )

                # Create the equipment intervention lines if they are not already linked to the request
                values_list.extend(
                    {
                        "request_id": request.id,
                        "equipment_id": link.equipment_id.id,
                        "event_id": intervention.id,
                        "start": intervention.start,
                        "operator_id": intervention.of_employee_id.id
                        or (intervention.of_employee_ids and intervention.of_employee_ids[0].id),
                        "event_link_id": link.id,
                    }
                    for link in event_equipment_links
                    if (request.id, link.equipment_id.id, intervention.id, link.id) not in current_values
                )
        values_list and self.env["of.service.request.equipment.line"].create(values_list)

    def _update_service_request_equipment_line(self, requests_data=None):
        """
        Updates the equipment lines in service requests based on the provided data.

        This method updates the equipment lines associated with service requests by
        replacing old equipment IDs with new ones as specified in the `requests_data`.

        Args:
            requests_data (dict, optional): A nested dictionary containing the mapping
                of request IDs to event IDs, event IDs to link IDs, and link IDs to
                dictionaries with old and new equipment IDs. The structure is as follows:
                    {request_id: {event_id: {link_id: {"old_equipment_id": int, "new_equipment_id": int}}}}
        """
        if requests_data is None:
            requests_data = {}
        for request, equipment_link_by_event in requests_data.items():
            for event, equipment_links in equipment_link_by_event.items():
                for link_id, link_values in equipment_links.items():
                    equipment_link = request.equipment_intervention_ids.filtered(
                        lambda line: line.event_id.id == event.id
                        and line.event_link_id.id == link_id
                        and line.equipment_id.id == link_values["old_equipment_id"]
                    )
                    if equipment_link.equipment_id.id != link_values["new_equipment_id"]:
                        equipment_link.equipment_id = link_values["new_equipment_id"]

    def _unlink_service_request_equipment_line(self, requests_data=None):
        """Unlink equipment intervention lines from service requests.

        If `requests_data` is provided, the method will remove the equipment intervention lines
        that are not linked to the request anymore based on the provided data.

        If `requests_data` is not provided, the method will remove the equipment intervention lines
        that are not linked to the request anymore.

        Args:
            requests_data (dict, optional): A dictionary containing request data in the format
                {request_id: {event_id: [equipment_ids]}}. Defaults to None.
        """
        if requests_data is None:
            requests_data = {}

        for request in self:
            # Remove equipment intervention lines if the equipment or the intervention are not linked to the
            # request anymore (e.g switch request of an event to another request)
            equipment_intervention_to_unlink = request.equipment_intervention_ids.filtered(
                lambda line: line.event_id.id not in request.intervention_ids.ids
                or not line.event_id.of_use_equipment
                or line.equipment_id.id not in request.equipment_ids.ids
            )
            equipment_intervention_to_unlink and equipment_intervention_to_unlink.unlink()

        # Remove equipment intervention lines if the equipment is not linked to an intervention of the
        # request anymore
        if requests_data:
            for request, equipments_removed_by_event in requests_data.items():
                for event, equipments_data in equipments_removed_by_event.items():
                    equipment_ids = list(map(lambda d: d["equipment_id"], equipments_data))
                    request.equipment_intervention_ids.filtered(
                        lambda line: line.event_id.id == event.id
                        and line.equipment_id.id in equipment_ids
                        and not line.event_link_id  # Link does not exist anymore here (removed from intervention)
                    ).unlink()

    def _prepare_service_request_equipment_link_values_from_equipment(self, equipment):
        """Prepare the values to create a service request equipment link.

        Args:
            equipment (recordset): The equipment record to link with the service request.

        Returns:
            dict: The values to create a service request equipment link.
        """
        self.ensure_one()
        return {
            "service_request_id": self.id,
            "equipment_id": equipment.id,
            "equipment_report_tmpl_id": self.default_equipment_report_tmpl_id.id or False,
            "task_id": self.default_equipment_report_tmpl_id.task_id.id or False,
        }
