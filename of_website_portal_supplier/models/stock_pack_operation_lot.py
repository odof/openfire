# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class StockPackOperationLot(models.Model):
    _inherit = 'stock.pack.operation.lot'

    of_expected_shipment_date = fields.Date(string=u"Date d’expédition prévue", copy=False)
    of_shipped_qty = fields.Float(string=u"Qté expédiée", copy=False)
