# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    of_use_equipment = fields.Boolean(
        string="Use Equipment", help="Activate this field to add one or more items of equipment to be worked on."
    )
    of_linked_equipment_ids = fields.One2many(
        comodel_name="of.calendar.event.equipment.link",
        inverse_name="event_id",
        string="Linked Equipments",
        compute="_compute_of_linked_equipment_ids",
        store=True,
        readonly=False,
    )
    of_equipment_ids = fields.Many2many(
        comodel_name="of.equipment",
        relation="of_calendar_event_equipment_rel",
        column1="intervention_id",
        column2="equipment_id",
        string="Equipments",
        compute="_compute_of_equipment_ids",
        store=True,
        readonly=False,
        help="Technical field to store the equipment linked to the calendar event, to easier access them.",
    )
    of_history_equipment_ids = fields.One2many(
        comodel_name="calendar.event",
        compute="_compute_of_history_equipment_ids",
        string="History (Equipment)",
    )
    of_default_equipment_report_tmpl_id = fields.Many2one(
        related="of_template_id.default_equipment_report_tmpl_id",
        string="Default Equipment Report Template",
        help="Technical field to get the default equipment report from the intervention template.",
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("of_task_id", "of_linked_equipment_ids", "of_linked_equipment_ids.task_id")
    def _compute_duration(self):
        events_with_equipment = self.filtered(lambda e: e.of_linked_equipment_ids)
        for event in events_with_equipment:
            if all(line.task_id for line in event.of_linked_equipment_ids):
                event.duration = sum(link.task_id.duration for link in event.of_linked_equipment_ids)
            else:
                line_without_task = event.of_linked_equipment_ids.filtered(lambda line: not line.task_id)
                line_with_task = event.of_linked_equipment_ids.filtered(lambda line: line.task_id)
                duration_with_task = sum(line_with_task.mapped("duration"))
                event.duration = (event.of_task_id.duration * len(line_without_task)) + duration_with_task

            # Fall back to the task duration if the request duration is still not set
            if not event.duration and event.of_task_id.duration:
                event.duration = event.of_task_id.duration

        super(CalendarEvent, self - events_with_equipment)._compute_duration()

    @api.depends("of_use_equipment", "of_address_id", "of_partner_id")
    def _compute_of_linked_equipment_ids(self):
        equipment_obj = self.env["of.equipment"]
        events_use_equipment = self.filtered(lambda e: e.of_use_equipment and not e.of_linked_equipment_ids)
        for event in events_use_equipment:
            equipments = equipment_obj.search(
                [("site_address_id", "=", event.of_address_id.id)]
            ) or equipment_obj.search([("customer_id", "=", event.of_address_id.id)])
            if not equipments and event.of_partner_id:
                equipments = equipment_obj.search([("customer_id", "=", event.of_partner_id.id)])

            event.of_linked_equipment_ids = (
                [
                    Command.create(
                        event._prepare_calendar_event_equipment_link_values_from_equipment(equipment=equipment)
                    )
                    for equipment in equipments
                ]
                if len(equipments) == 1
                else False
            )

        for request in self - events_use_equipment:
            request.of_linked_equipment_ids = request.of_linked_equipment_ids

    @api.depends("of_equipment_ids")
    def _compute_of_history_intervention_ids(self):
        super()._compute_of_history_intervention_ids()
        for event in self:
            interventions = self.env["calendar.event"].browse()
            if event.of_address_id:
                interventions = event.of_address_id.of_intervention_address_ids
            elif event.of_partner_id:
                interventions = event.of_partner_id.of_intervention_partner_ids

            event.of_history_intervention_ids = (
                self.search(
                    [
                        ("id", "in", interventions.ids),
                        ("start", "<", event.start),
                        "|",
                        ("of_equipment_ids", "=", False),
                        ("of_equipment_ids", "not in", event.of_equipment_ids.ids),
                    ]
                )
                if interventions
                else False
            )

    @api.depends("of_linked_equipment_ids", "of_linked_equipment_ids.equipment_id")
    def _compute_of_equipment_ids(self):
        events_with_equipment = self.filtered("of_linked_equipment_ids")
        for request in events_with_equipment:
            request.of_equipment_ids = request.of_linked_equipment_ids.mapped("equipment_id")
        for request in self - events_with_equipment:
            request.of_equipment_ids = False

    @api.depends("of_equipment_ids")
    def _compute_of_history_equipment_ids(self):
        events_with_equipment = self.filtered(lambda e: e.of_equipment_ids)
        for event in events_with_equipment:
            event.of_history_equipment_ids = event.mapped("of_equipment_ids.intervention_ids").filtered(
                lambda i: event.start > i.start
            )
        for event in self - events_with_equipment:
            event.of_history_equipment_ids = self.env["calendar.event"].browse()

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def write(self, vals):
        if (
            "of_equipment_ids" in vals
            or "of_linked_equipment_ids" in vals
            and any(event.of_state in ("done", "cancel") for event in self)
        ):
            raise UserError(_("You cannot change the equipment of done or cancelled events."))
        return super().write(vals)

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_open_intervention(self):
        self.ensure_one()
        view_id = self.env.ref("of_planning.calendar_event_view_form").id
        return {
            "type": "ir.actions.act_window",
            "name": "Interventions",
            "res_model": "calendar.event",
            "res_id": self.ids[0],
            "view_mode": "form",
            "views": [[view_id, "form"]],
            "target": "current",
        }

    def action_button_add_equipments_to_event(self):
        self.ensure_one()
        view = self.env.ref("of_equipment.of_equipment_link_create_form_view")
        return {
            "name": _("Add Equipment to Event"),
            "res_model": "of.equipment.link.create.wizard",
            "view_mode": "form",
            "view_id": view.id,
            "context": {"default_event_id": self.id},
            "target": "new",
            "type": "ir.actions.act_window",
        }

    def action_button_remove_all_equipments(self):
        self.ensure_one()
        self.of_linked_equipment_ids.unlink()
        return True

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _prepare_calendar_event_equipment_link_values_from_equipment(self, equipment):
        """Prepare the values to create a calendar event equipment link from an equipment record.

        Args:
            equipment (recordset): The equipment record to link with the service request.

        Returns:
            dict: The values to create a calendar event equipment link.
        """
        self.ensure_one()
        return {
            "event_id": self.id,
            "equipment_id": equipment.id,
            "equipment_report_tmpl_id": self.of_template_id.default_equipment_report_tmpl_id.id or False,
            "task_id": self.of_template_id and self.of_template_id.default_equipment_report_tmpl_id.task_id.id or False,
        }
