# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.tools.safe_eval import safe_eval


class OFServiceRequestCreateInterventionWizard(models.TransientModel):
    _name = "of.service.request.create.intervention.wizard"
    _description = "Wizard for creating Intervention from Service Requests"

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Operator")
    start_date = fields.Datetime()
    line_ids = fields.One2many(
        comodel_name="of.service.request.create.intervention.line.wizard", inverse_name="wizard_id", string="Lines"
    )
    show_warning = fields.Boolean(string="Warning", compute="_compute_show_warning")

    @api.depends("employee_id", "start_date", "line_ids")
    def _compute_show_warning(self):
        for rec in self:
            if rec.employee_id and rec.start_date and rec.line_ids:
                start_date = rec.start_date
                end_date = start_date
                for request in rec.mapped("line_ids.request_id"):
                    end_date += relativedelta(hours=request.duration)
                events = self.env["calendar.event"].search(
                    [
                        ("of_employee_ids", "in", rec.employee_id.id),
                        ("start_date", "<", end_date),
                        ("stop_date", ">", start_date),
                        ("of_state", "not in", ["cancel", "postponed"]),
                    ],
                    limit=1,
                )
                rec.show_warning = bool(events)
            else:
                rec.show_warning = False

    def _get_create_intervention_values(self, request):
        self.ensure_one()
        return {
            "of_partner_id": request.partner_id.id,
            "of_address_id": request.address_id.id,
            "of_task_id": request.task_id.id,
            "of_template_id": request.template_id.id,
            "of_request_id": request.id,
            "of_employee_id": self.employee_id.id,
            "of_employee_ids": [Command.link(self.employee_id.id)],
            "of_tag_ids": [Command.link(tag.id) for tag in request.tag_ids],
            "duration": request.duration,
            "user_id": self.env.user.id,
            "of_company_id": request.company_id.id,
            "of_internal_description": request.note,
            "of_order_id": request.order_id.id,
        }

    def action_button_create_intervention(self):
        self.ensure_one()

        event_obj = self.env["calendar.event"]
        created_interventions = self.env["calendar.event"]
        if not self._context.get("tz"):
            self = self.with_context(tz="Europe/Paris")

        current_date = self.start_date
        for request in self.line_ids.mapped("request_id"):
            end_date = current_date + relativedelta(hours=request.duration)

            name_parts = [request.address_id.name_get()[0][1]] if request.address_id else ["Intervention"]
            name_parts += [
                getattr(request.address_id, field) for field in ("zip", "city") if getattr(request.address_id, field)
            ]
            name = " ".join(name_parts)

            vals = self._get_create_intervention_values(request)
            vals.update({"name": name, "start": current_date, "stop": end_date})

            intervention = event_obj.create(vals)
            created_interventions |= intervention

            current_date = end_date

        action = self.env.ref("of_planning.action_calendar_event").read()[0]
        context = safe_eval(action["context"])
        context["force_date_start"] = created_interventions[0].start
        action["context"] = context
        action["domain"] = [("id", "in", created_interventions.ids)]
        return action


class OFServiceRequestCreateInterventionLineWizard(models.TransientModel):
    _name = "of.service.request.create.intervention.line.wizard"
    _description = "Wizard line for creating Intervention from Service Requests"
    _order = "sequence"

    wizard_id = fields.Many2one(comodel_name="of.service.request.create.intervention.wizard", string="Wizard")
    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(comodel_name="of.service.request", string="Service Request", required=True)
    request_number = fields.Char(string="Number", related="request_id.number")
    request_title = fields.Char(string="Title", related="request_id.title")
    request_partner_id = fields.Many2one(comodel_name="res.partner", string="Partner", related="request_id.partner_id")
    request_address_zip = fields.Char(string="Zip Code", related="request_id.address_zip")
    request_address_city = fields.Char(string="City", related="request_id.address_city")
    request_task_id = fields.Many2one(comodel_name="of.planning.task", string="Task", related="request_id.task_id")
