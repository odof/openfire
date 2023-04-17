# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_validated_by_carrier = fields.Boolean(string="Validé par le transporteur")
