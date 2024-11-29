# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, _, api, fields, models, tools


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_request_ids = fields.One2many(
        comodel_name="of.service.request",
        inverse_name="order_id",
        string="Service Requests",
        copy=False,
        store=True,
    )
    of_request_count = fields.Integer(string="Service Requests count", compute="_compute_of_request_count")
    of_origin_request_id = fields.Many2one(comodel_name="of.service.request", string="Demande d'intervention d'origine")

    @api.depends("of_request_ids", "order_line.of_request_line_id")
    def _compute_of_request_count(self):
        for order in self:
            requests = order.of_request_ids.filtered(lambda s: s.state != "cancel")
            requests |= order.mapped("order_line.of_request_line_id.request_id")
            order.of_request_ids = requests
            order.of_request_count = len(requests)

    def action_button_view_request(self):
        self.ensure_one()
        return self._get_action_view_request(self.of_request_ids)

    def _get_action_view_request(self, requests):
        """Return an action to display the service requests linked to the sale order"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("of_service.action_of_service_request")
        date_today = fields.Datetime.now()
        fortnight_date = date_today + timedelta(days=14)  # arbitrary date in the future, 2 weeks from now
        action["context"] = {
            "default_partner_id": self.partner_id.id,
            "default_address_id": self.partner_shipping_id.id or self.partner_id.id,
            "default_recurrency": False,
            "default_next_date": date_today,
            "default_stop_date": fortnight_date,
            "default_origin": _("[Order] %s") % self.name,
            "default_order_id": self.id,
            "default_type_id": self.env.ref("of_service.of_service_request_type_installation").id,
        }
        # Choose the view_mode accordingly
        if not requests or len(requests) > 1:
            action["domain"] = [("id", "in", requests.ids)]
        elif len(requests) == 1:
            form_view = self.env.ref("of_service.of_service_request_view_form", raise_if_not_found=False)
            # Put the form view in first position
            action["views"] = [(form_view and form_view.id or False, "form")] + [
                (state, view) for state, view in action.get("views", []) if view != "form"
            ]
            action["res_id"] = requests.id
        return action

    def action_button_schedule_intervention(self):
        self.ensure_one()
        date_today = fields.Datetime.now()
        fortnight_date = date_today + timedelta(days=14)  # arbitrary date in the future, 2 weeks from now
        return {
            "type": "ir.actions.act_window",
            "name": _("Schedule an intervention"),
            "res_model": "of.service.request",
            "view_mode": "form",
            "view_id": self.env.ref("of_service.of_service_request_view_form").id,
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_address_id": self.partner_shipping_id.id or self.partner_id.id,
                "default_recurrency": False,
                "default_next_date": date_today,
                "default_stop_date": fortnight_date,
                "default_origin": _("[Order] %s") % self.name,
                "default_order_id": self.id,
                "hide_schedule_button": True,
                "default_type_id": self.env.ref("of_service.of_service_request_type_installation").id,
            },
        }

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order_template = order.sale_order_template_id
            if order_template and order_template.of_service_mgmt == "sale":
                service_request = self.env["of.service.request"].create(
                    {
                        "partner_id": order.partner_id.id,
                        "address_id": order.partner_shipping_id.id,
                        "template_id": order_template.of_intervention_template_id.id or False,
                        "task_id": order_template.of_intervention_template_id.task_id.id or False,
                        "type_id": order_template.of_intervention_template_id.type_id.id,
                        "fiscal_position_id": order_template.of_intervention_template_id.fiscal_position_id.id
                        or order.fiscal_position_id.id,
                        "company_id": order.company_id.id,
                        "user_id": False,
                        "duration": order_template.of_intervention_template_id.task_id.duration,
                        "recurrency": False,
                        "next_date": order.commitment_date,
                        "note": tools.html2plaintext(order.of_intervention_notes),
                        "order_id": order.id,
                        "origin": _("[Order] %s") % self.name,
                        "stage_id": self.env.ref("of_service.of_service_request_stage_new").id,
                    }
                )
                lines_to_create = []
                lines_to_create.extend(
                    Command.create(line._prepare_request_service_line_vals(service_request))
                    for line in order_template.of_intervention_template_id.line_ids
                )
                if lines_to_create:
                    service_request.line_ids = lines_to_create
                    service_request._recompute_taxes()
                service_request.end_date = service_request._get_end_date()
        return res
