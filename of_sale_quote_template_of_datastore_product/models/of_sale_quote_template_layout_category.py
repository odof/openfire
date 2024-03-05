# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OfSaleQuoteTemplateLayoutCategory(models.Model):
    _name = 'of.sale.quote.template.layout.category'
    _inherit = ['of.sale.quote.template.layout.category', 'of.datastore.product.reference']
