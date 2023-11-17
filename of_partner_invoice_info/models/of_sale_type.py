# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleType(models.Model):
    _inherit = 'of.sale.type'

    invoice_info_exclusion = fields.Boolean(string=u"Exclure du calcul d'encours")
