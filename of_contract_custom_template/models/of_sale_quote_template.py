# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleQuoteTemplate(models.Model):
    _inherit = 'sale.quote.template'

    of_contract_tmpl_id = fields.Many2one(comodel_name='of.contract.template', string=u"Modèle de contrat")
