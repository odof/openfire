# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_standard_id = fields.Many2one(comodel_name='of.product.standard', string="Standard")
    of_standard_description = fields.Text(
        string="Standard description",
        translate=True,
        compute='_compute_of_standard_description',
        store=True,
        readonly=False,
    )

    @api.depends('of_standard_id')
    def _compute_of_standard_description(self):
        for product_tmpl in self:
            product_tmpl.of_standard_description = product_tmpl.of_standard_id.description or False
