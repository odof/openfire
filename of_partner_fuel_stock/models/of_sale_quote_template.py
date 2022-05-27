# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class OFSaleQuoteLine(models.Model):
    _inherit = 'sale.quote.line'

    of_storage = fields.Boolean(string='Storage and withdrawal on demand of articles', defaut=False)
