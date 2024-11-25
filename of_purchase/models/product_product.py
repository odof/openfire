# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    of_purchase_coeff = fields.Float(string="Purchase coefficient", company_dependent=True)
    of_purchase_count = fields.Integer(compute="compute_of_purchase_count", string="Purchases")

    @api.depends("categ_id.of_sale_cost", "cost_method")
    def compute_of_purchase_coefficient(self, value):
        for product in self:
            if product.cost_method not in ("average", "fifo") or product.categ_id.of_sale_cost == "standard":
                product.of_purchase_coeff_cost_propagation(value)

    def of_purchase_coeff_cost_propagation(self, cost):
        # Le coefficient d'achat (of_purchase_coeff) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env["res.company"].search(["|", ("chart_template_id", "!=", False), ("parent_id", "=", False)])
        property_obj = self.env["ir.property"].sudo()
        coeff_values = {
            product.id: cost and product.of_seller_price and cost / product.of_seller_price or 1 for product in self
        }
        for company in companies:
            property_obj.with_context(force_company=company.id)._set_multi(
                "of_purchase_coeff", "product.product", coeff_values
            )

    def of_purchase_coeff_seller_price_propagation(self, seller_price):
        # Le coefficient d'achat (of_purchase_coeff) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env["res.company"].search(["|", ("chart_template_id", "!=", False), ("parent_id", "=", False)])
        property_obj = self.env["ir.property"].sudo()
        coeff_values = {}
        for product in self:
            cost = product.get_cost()
            coeff_values[product.id] = cost and seller_price and cost / seller_price or 1
        for company in companies:
            property_obj.with_context(force_company=company.id)._set_multi(
                "of_purchase_coeff", "product.product", coeff_values
            )

    def compute_of_purchase_count(self):
        domain = [
            ("product_id", "in", self.mapped("id")),
        ]
        PurchaseOrderLines = self.env["purchase.order.line"].search(domain)
        for product in self:
            product.of_purchase_count = len(
                PurchaseOrderLines.filtered(lambda r: r.product_id == product).mapped("order_id")
            )
