# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionAdditionalLine(models.Model):
    _name = 'of.planning.intervention.template.additional.line'
    _description = "Additional Products"

    product_id = fields.Many2one(
        comodel_name='product.product', string="Product", domain=[('product_tmpl_id.of_mobile_available', '=', True)]
    )
    price_unit = fields.Float(
        string="Unit price",
        digits='Product Price',
        related="product_id.list_price",
        default=0.0,
        readonly=True,
    )
    additional_template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template',
        string="Additional Template",
        ondelete='cascade',
    )
