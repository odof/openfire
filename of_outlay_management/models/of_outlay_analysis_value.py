# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

OUTLAY_VALUE_TYPES = [
    ('income_expected', u"CA"),
    ('income_invoiced', u"Recettes"),
    ('expense_expected', u"Dépenses estimées"),
    ('expense_ordered', u"Dépenses prévisionnelles"),
    ('expense_invoiced', u"Dépenses"),
]


class OFOutlayAnalysisValue(models.Model):
    _name = 'of.outlay.analysis.value'
    _description = u"Valeurs d'analyse des débours"

    analysis_id = fields.Many2one(
        comodel_name='of.outlay.analysis', string=u"Analyse de débours", required=True, ondelete='cascade')
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string=u"Compte analytique")
    analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")
    date = fields.Date(required=True)
    type = fields.Selection(selection=OUTLAY_VALUE_TYPES, string=u"Type", required=True)
    amount = fields.Float(string=u"Montant")
