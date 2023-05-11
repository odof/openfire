# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_standard_id = fields.Many2one('of.product.standard', string="Standard", ondelete='set null')
    of_description_standard = fields.Text("Standard description", translate=True)

    @api.onchange('of_standard_id')
    def _onchange_of_standard_id(self):
        for product_tmpl in self:
            product_tmpl.of_description_standard = product_tmpl.of_standard_id.description or False
