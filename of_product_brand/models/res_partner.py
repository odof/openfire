# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    brand_ids = fields.One2many(
        comodel_name='of.product.brand', inverse_name='partner_id', string="Brands", readonly=True
    )
    supplier_brand_count = fields.Integer(compute='_compute_supplier_brand_count', string="# Brands")

    @api.depends('brand_ids')
    def _compute_supplier_brand_count(self):
        for partner in self:
            partner.supplier_brand_count = len(partner.brand_ids)
