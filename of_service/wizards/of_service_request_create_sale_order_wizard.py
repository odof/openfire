# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFServiceRequestCreateSaleOrderWizard(models.TransientModel):
    _name = "of.service.request.create.sale.order.wizard"
    _description = "Wizard for creating Sale Order from Service Requests"

    @api.model
    def default_get(self, field_list=None):
        default_values = super().default_get(field_list)
        context = self.env.context
        active_model = context.get("active_model", "")
        if active_model == "of.service.request":
            service_id = context["active_ids"][0]
            service = self.env["of.service.request"].browse(service_id)
            default_values.update(
                {
                    "service_request_id": service_id,
                    "template_id": service.template_id.id,
                    "partner_id": service.partner_id.id,
                    "partner_invoice_id": service.partner_id.id,
                    "partner_shipping_id": service.address_id.id,
                    "sale_order_template_id": service.template_id.default_sale_order_template_id.id,
                    "fiscal_position_id": service.fiscal_position_id.id,
                    "pricelist_id": service.partner_id.property_product_pricelist.id,
                    "client_order_ref": f"{service.number} - {service.title}",
                }
            )
        return default_values

    service_request_id = fields.Many2one(comodel_name="of.service.request", string="Demande d'intervention")
    template_id = fields.Many2one(comodel_name="of.planning.intervention.template", string="Modèle d'intervention")
    sale_order_template_ids = fields.Many2many(related="template_id.sale_order_template_ids")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Client", required=True)
    partner_invoice_id = fields.Many2one(comodel_name="res.partner", string="Adresse de facturation", required=True)
    partner_shipping_id = fields.Many2one(comodel_name="res.partner", string="Adresse d'expédition", required=True)
    sale_order_template_id = fields.Many2one(
        comodel_name="sale.order.template",
        string="Modèle de devis",
    )
    fiscal_position_id = fields.Many2one(comodel_name="account.fiscal.position", string="Position fiscale")
    pricelist_id = fields.Many2one(comodel_name="product.pricelist", string="Liste de prix")
    client_order_ref = fields.Char(string="Référence client")

    def _get_create_sale_order_values(self):
        self.ensure_one()
        return {
            "partner_id": self.partner_id.id,
            "partner_invoice_id": self.partner_invoice_id.id,
            "partner_shipping_id": self.partner_shipping_id.id,
            "sale_order_template_id": self.sale_order_template_id.id,
            "fiscal_position_id": self.fiscal_position_id.id,
            "pricelist_id": self.pricelist_id.id,
            "client_order_ref": self.client_order_ref,
            "of_origin_request_id": self.service_request_id.id,
        }

    def action_button_create_sale_order(self):
        self.ensure_one()
        context = self.env.context.copy()

        vals = self._get_create_sale_order_values()

        order = self.env["sale.order"].create(vals)
        order._onchange_sale_order_template_id()

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_type": "form",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": order.id,
            "target": "current",
            "context": context,
            "flags": {"initial_mode": "edit", "form": {"options": {"mode": "edit"}}},
        }
