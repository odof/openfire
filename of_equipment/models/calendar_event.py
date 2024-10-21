# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

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
                event.duration = sum(link.task_duration for link in event.of_linked_equipment_ids)
            else:
                line_without_task = event.of_linked_equipment_ids.filtered(lambda line: not line.task_id)
                line_with_task = event.of_linked_equipment_ids.filtered(lambda line: line.task_id)
                duration_with_task = sum(line_with_task.mapped("task_duration"))
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
            ("of_equipment_ids" in vals or "of_linked_equipment_ids" in vals)
            and any(event.of_state in ("done", "cancel") for event in self)
            and not self.env.context.get("of_ignore_event_state")
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

    def action_button_send_email(self):
        self.ensure_one()
        composer_action = super().action_button_send_email()

        # Add the equipment attached report template to the mail composer when sending the email from
        # the calendar event.
        composer = self.env["mail.compose.message"].browse(composer_action["res_id"])
        attachments = self._create_equipment_link_report_to_send()
        composer.write({"attachment_ids": [Command.link(attachment.id) for attachment in attachments]})
        return composer_action

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
            "equipment_report_tmpl_id": self.of_default_equipment_report_tmpl_id.id or False,
            "task_id": self.of_default_equipment_report_tmpl_id.task_id.id or False,
        }

    def _send_report_post_hook_composer_onchange_template(self, composer):
        result = super()._send_report_post_hook_composer_onchange_template(composer)

        # Add the equipment attached report template to the mail composer when sending the email through automation.
        self._add_equipment_attached_report_template_to_composer(composer)
        return result

    def _create_equipment_link_report_to_send(self):
        """
        Generate and attach equipment link reports.



        Returns:
            list: A list of attachment IDs for the generated equipment link reports.
        """
        if not (equipment_links := self._report_get_equipment_links_print_mode_attached()):
            return []  # No equipment links to print in attached mode.

        reports_data = []
        for equipment_lnk in equipment_links:
            report_bin, report_format = self.env["ir.actions.report"]._render(
                "of_equipment.report_action_equipment_report", [equipment_lnk.id]
            )
            reports_data.append(
                {
                    "name": f"{equipment_lnk._get_report_base_filename()}.{report_format}",
                    "datas": base64.b64encode(report_bin),
                }
            )

        return self.env["ir.attachment"].create(reports_data)

    def _add_equipment_attached_report_template_to_composer(self, composer):
        """Add the equipment separated report template to the mail composer.

        Args:
            composer (recordset): The mail composer record to add the equipment separated report template to.
        """
        self.ensure_one()

        if attachments := self._create_equipment_link_report_to_send():
            composer.attachment_ids += attachments

    def _report_get_equipment_links_print_mode_merged(self):
        """Get equipments to print in the report in merged mode.

        Returns:
            recordset: The equipment links to print in the report in merged mode.
        """
        self.ensure_one()
        return self.of_linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_report_tmpl_id.sending_report_mode == "merged"
        )

    def _report_get_equipment_links_print_mode_attached(self):
        """Get equipments to print in the report in attached mode.

        Returns:
            recordset: The equipment links to print in the report in attached mode.
        """
        self.ensure_one()
        return self.of_linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_report_tmpl_id.sending_report_mode == "attached"
        )
