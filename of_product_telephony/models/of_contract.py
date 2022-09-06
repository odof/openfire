# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFContractLine(models.Model):
    _inherit = 'of.contract.line'

    external_description = fields.Text(string=u"Description externe")
    order_line_id = fields.Many2one(comodel_name='sale.order.line', string=u"Ligne de commande")
