# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleQuoteLine(models.Model):
    _name = 'of.planning.intervention.line'
    _inherit = ['of.planning.intervention.line', 'of.datastore.product.reference']
