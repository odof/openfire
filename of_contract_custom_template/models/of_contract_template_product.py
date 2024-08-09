# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFContractTemplateProduct(models.Model):
    _name = 'of.contract.template.product'
    _order = 'sequence'

    name = fields.Text(string=u"Description", required=True)
    sequence = fields.Integer(string=u"Séquence", default=10, help=u"Séquence")
    line_id = fields.Many2one(
        comodel_name='of.contract.template.line', string=u"Ligne de modèle de contrat",
        ondelete='cascade', required=True
    )
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", required=True)
    price_unit = fields.Float(string=u"Prix unitaire")
    purchase_price = fields.Float(string=u"Coût")
    quantity = fields.Float(string=u"Qté", default=1.0)
    tax_ids = fields.Many2many(
        comodel_name='account.tax', string=u"Taxes", domain=[('type_tax_use', '=', 'sale')], copy=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            product = self.product_id
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
            self.price_unit = product.list_price
            self.purchase_price = product.get_cost()
            self.tax_ids = product.taxes_id

    @api.multi
    def get_contract_product_vals(self):
        self.ensure_one()
        fpos = self.line_id.contract_tmpl_id.property_fiscal_position_id
        company = self.env.user.company_id
        taxes = company._of_filter_taxes(self.product_id.taxes_id)
        taxes = fpos.map_tax(taxes, self.product_id) if fpos else taxes
        return {
            'product_id': self.product_id.id,
            'price_unit': self.price_unit,
            'purchase_price': self.purchase_price,
            'quantity': self.quantity,
            'tax_ids': [(4, tax.id) for tax in taxes],
            'name': self.product_id.name_get()[0][1]
            + '\n'
            + (self.product_id.description_sale if self.product_id.description_sale else ''),
        }
