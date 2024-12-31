# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_yousign_request_count = fields.Integer(
        string="Number of YouSign requests",
        compute="_compute_of_yousign_request_ids",
    )
    of_yousign_request_ids = fields.Many2many(
        comodel_name="of.yousign.request",
        string="YouSign requests",
        compute="_compute_of_yousign_request_ids",
        search="_search_of_yousign_request_ids",
    )
    of_yousign_requests_needupdate = fields.Boolean(
        string="YouSign requests to update",
        compute="_compute_of_yousign_request_ids",
    )

    @api.depends()
    def _compute_of_yousign_request_ids(self):
        yousign_request_obj = self.env["of.yousign.request"]
        for record in self:
            requests = yousign_request_obj.search(
                [
                    ("model", "=", "sale.order"),
                    ("res_id", "=", record.id),
                    ("state", "!=", "cancel"),
                ]
            )
            if requests:
                record.of_yousign_request_count = len(requests)
                record.of_yousign_request_ids = requests
                record.of_yousign_requests_needupdate = bool(
                    requests.filtered(lambda r: r.state in ("sent", "signed"))
                )
            else:
                record.of_yousign_request_count = 0
                record.of_yousign_request_ids = False
                record.of_yousign_requests_needupdate = False

    @api.model
    def _search_of_yousign_request_ids(self, operator, value):
        domain = [("model", "=", "sale.order"), ("state", "!=", "cancel")]
        if operator == "=":
            domain += [("state", "=", value)]
        elif operator == "in":
            domain += [("state", "in", value)]
        requests = self.env["of.yousign.request"].search(domain)
        # On ne veut surtout pas charger l'ensemble des données yousign en cache
        return [
            ("id", "in", requests.with_context(prefetch_fields=False).mapped("res_id"))
        ]

    def action_view_yousing_request(self):
        self.ensure_one()
        action = self.env.ref("of_yousign_connector.action_of_yousign_request").read()[0]
        action["domain"] = [("model", "=", "sale.order"), ("res_id", "=", self.id)]
        return action

    def action_yousign_direct_signature_wizard(self):
        self.ensure_one()
        yousign_request_obj = self.env["of.yousign.request"]
        requests = yousign_request_obj.search(
            [
                ("model", "=", "sale.order"),
                ("res_id", "=", self.id),
                ("state", "!=", "cancel"),
            ]
        )
        context = {
            "default_model": "sale.order",
            "default_res_id": self.id,
        }
        if requests:
            context["default_request_id"] = requests[0].id
        return {
            "type": "ir.actions.act_window",
            "name": _("Quote signing"),
            "res_model": "yousign.direct.signature.wizard",
            "view_mode": "form",
            "view_type": "form",
            "view_id": self.env.ref(
                "of_yousign_connector.of_yousign_direct_signature_wizard_view_form"
            ).id,
            "target": "new",
            "context": context,
        }

    def yousign_update_status(self):
        self.ensure_one()
        # filters are done in the respective methods
        # self.of_yousign_request_ids.update_status()
        # self.of_yousign_request_ids.archive()

    def _auto_send_yousign_request(self, signatory_data={}):
        self.ensure_one()
        context = self._context.copy()
        context.update(
            {
                "active_model": "sale.order",
                "active_id": self.id,
            }
        )
        # Uses a lot of context in default_get which is enough to create one
        request = self.env["of.yousign.request"].with_context(context).create({})
        # request._onchange_of_template_id()
        if signatory_data:
            request.write({"signatory_ids": [(5,), (0, 0, signatory_data)]})
        return request
