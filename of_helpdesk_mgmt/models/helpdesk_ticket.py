# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import api, fields, models, tools


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    of_lead_ids = fields.One2many(comodel_name="crm.lead", inverse_name="of_ticket_id", string="Opportunités")
    of_lead_count = fields.Integer(string="# Opportunités", compute="_compute_of_lead_count")
    of_service_request_ids = fields.One2many(
        comodel_name="of.service.request", inverse_name="ticket_id", string="DI"
    )
    of_service_request_count = fields.Integer(string="# DI", compute="_compute_of_service_request_count")
    of_due_date = fields.Datetime(string="Date d'échéance")

    @api.depends("of_lead_ids")
    def _compute_of_lead_count(self):
        for ticket in self:
            ticket.of_lead_count = len(ticket.of_lead_ids)

    @api.depends("of_service_request_ids")
    def _compute_of_service_request_count(self):
        for ticket in self:
            ticket.of_service_request_count = len(ticket.of_service_request_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update({'of_due_date': datetime.now() + timedelta(days=1)})
        return super().create(vals_list)

    def action_button_view_lead(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_all_leads")
        action["context"] = {
            "default_name": self.name,
            "default_type": "opportunity",
            "default_partner_id": self.partner_id.id,
            "default_of_ticket_id": self.id,
            "default_user_id": False,
            "default_of_canvasser_id": self.user_id.id,
            "default_description": self.description,
            "default_medium_id": 11,
        }
        # Choose the view_mode accordingly
        if not self.of_lead_ids or len(self.of_lead_ids) > 1:
            action["domain"] = [("id", "in", self.of_lead_ids.ids)]
        elif len(self.of_lead_ids) == 1:
            form_view = self.env.ref("crm.crm_lead_view_form", raise_if_not_found=False)
            # Put the form view in first position
            action["views"] = [(form_view and form_view.id or False, "form")] + [
                (state, view) for state, view in action.get("views", []) if view != "form"
            ]
            action["res_id"] = self.of_lead_ids.id
        return action

    def action_button_view_service_request(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("of_service.action_of_service_request")
        end_date = self.create_date + timedelta(days=14)
        template = self.env["of.planning.intervention.template"].search([("name", "=", "SAV")])
        action["context"] = {
            "default_title": self.name,
            "default_partner_id": self.partner_id.id,
            "default_address_id": self.partner_id.id,
            "default_template_id": template.id,
            "default_task_id": template.task_id.id,
            "default_company_id": self.company_id.id,
            "default_user_id": self.user_id.id,
            "default_recurrency": False,
            "default_next_date": self.create_date,
            "default_end_date": end_date,
            "default_note": tools.html2plaintext(self.description),
            "default_origin": "[Commande] %s" % self.name,
            "default_ticket_id": self.id,
            "default_type_id": self.env.ref("of_equipment_service.of_service_request_type_after_sales").id,
            "default_stage_id": self.env.ref("of_service.of_service_request_stage_new").id,
        }
        # Choose the view_mode accordingly
        if not self.of_service_request_ids or len(self.of_service_request_ids) > 1:
            action["domain"] = [("id", "in", self.of_service_request_ids.ids)]
        elif len(self.of_service_request_ids) == 1:
            form_view = self.env.ref("of_service.of_service_request_view_form", raise_if_not_found=False)
            # Put the form view in first position
            action["views"] = [(form_view and form_view.id or False, "form")] + [
                (state, view) for state, view in action.get("views", []) if view != "form"
            ]
            action["res_id"] = self.of_service_request_ids.id
        return action

    def action_create_lead(self):
        self.ensure_one()
        lead = self.env["crm.lead"].create(
            {
                "name": self.name,
                "type": "opportunity",
                "partner_id": self.partner_id.id,
                "of_ticket_id": self.id,
                "user_id": False,
                "of_canvasser_id": self.user_id.id,
                "description": self.description,
                "medium_id": 11,
            }
        )
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_all_leads")
        form_view = self.env.ref("crm.crm_lead_view_form", raise_if_not_found=False)
        action["views"] = [(form_view and form_view.id or False, "form")] + [
            (state, view) for state, view in action.get("views", []) if view != "form"
        ]
        action["res_id"] = lead.id
        return action

    def action_create_service_request(self):
        self.ensure_one()
        end_date = self.create_date + timedelta(days=14)
        template = self.env["of.planning.intervention.template"].search([("name", "=", "SAV")])
        service_request = self.env["of.service.request"].create(
            {
                "title": self.name,
                "partner_id": self.partner_id.id,
                "address_id": self.partner_id.id,
                "template_id": template.id,
                "task_id": template.task_id.id,
                "company_id": self.company_id.id,
                "user_id": self.user_id.id,
                "recurrency": False,
                "next_date": self.create_date,
                "end_date": end_date,
                "note": tools.html2plaintext(self.description),
                "origin": "[Commande] %s" % self.name,
                "ticket_id": self.id,
                "type_id": self.env.ref("of_equipment_service.of_service_request_type_after_sales").id,
                "stage_id": self.env.ref("of_service.of_service_request_stage_new").id,
            }
        )
        action = self.env["ir.actions.actions"]._for_xml_id("of_service.action_of_service_request")
        form_view = self.env.ref("of_service.of_service_request_view_form", raise_if_not_found=False)
        action["views"] = [(form_view and form_view.id or False, "form")] + [
            (state, view) for state, view in action.get("views", []) if view != "form"
        ]
        action["res_id"] = service_request.id
        return action
