# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.misc import formatLang
import json

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    of_impression_acomptes = fields.Selection(
        [('as_payment', u"Faire apparaître les paiements des factures d'acompte avec les paiements de la facture finale"),
         ('line', u"Faire apparaître les lignes d'acompte avec les articles")], string=u"(OF) Acomptes",
        help=u"Si les acomptes apparaissent comme des paiements alors le total HT, la TVA, le total de la TVA et montant dû seront en fonction des montants de la commande et non ceux de la facture.",
        default='line',
        required=True)

    @api.multi
    def set_of_impression_acomptes_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_impression_acomptes', self.of_impression_acomptes)
