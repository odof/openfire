# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningInterventionTemplateLine(models.Model):
    _name = "of.planning.intervention.template.line"
    _description = "Intervention template's line"

    template_id = fields.Many2one(comodel_name="of.planning.intervention.template", string="Template", required=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    price_unit = fields.Float(
        string="Price unit",
        digits="Product Price",
        default=0.0,
        compute="_compute_price_unit",
        store=True,
        readonly=False,
    )
    qty = fields.Float(digits="Product Unit of Measure", compute="_compute_qty", store=True, readonly=False)
    name = fields.Text(string="Description", compute="_compute_name", store=True, readonly=False)

    @api.depends("product_id")
    def _compute_qty(self):
        for record in self:
            record.qty = 1

    @api.depends("product_id")
    def _compute_price_unit(self):
        for record in self:
            product = record.product_id
            record.price_unit = product.lst_price

    @api.depends("product_id")
    def _compute_name(self):
        for record in self:
            if product := record.product_id:
                name = product.name_get()[0][1]
                if product.description_sale:
                    name += "\n" + product.description_sale
                record.name = name
            else:
                record.name = ""

    def _prepare_intervention_line_vals(self, event):
        self.ensure_one()
        if not event:
            return {}
        return {
            "product_id": self.product_id.id,
            "price_unit": self.price_unit,
            "qty": self.qty,
            "name": self.name,
            "intervention_id": event.id,
        }
