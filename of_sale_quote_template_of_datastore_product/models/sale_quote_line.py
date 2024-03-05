# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleQuoteLine(models.Model):
    _name = 'sale.quote.line'
    _inherit = ['sale.quote.line', 'of.datastore.product.reference']
