# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

OUTLAY_LINE_TYPES = [
    ('income', u"Produits ou ventes"),
    ('expense', u"Charges ou débours"),
    ('stock', u"Stocks consommés"),
    # ('', u"Temps"),
    ('misc', u"OD comptables"),
    ('margin_theoretical', u"Marge théorique"),
    ('margin_objective', u"Marge objectif"),
    ('margin_real', u"Marge réelle"),
    ('income_expected', u"Facturation théorique"),
    ('to_invoice', u"Facture à établir"),
    ('expense_remaining', u"Gap charges"),
]


class OFOutlayAnalysisLine(models.Model):
    _name = 'of.outlay.analysis.line'
    _description = u"Lignes d'analyse des débours"
    _order = 'analytic_section_id, id'

    @api.model
    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    analysis_id = fields.Many2one(comodel_name='of.outlay.analysis', string=u"Analyse de débours", required=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='analysis_id.currency_id', string=u"Devise", readonly=True
    )
    analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")
    type = fields.Selection(selection=OUTLAY_LINE_TYPES, string=u"Type", required=True)

    amount_init = fields.Monetary(string=u"Montant initial", currency_field='currency_id')
    amount_compl = fields.Monetary(string=u"Montant complémentaire", currency_field='currency_id')
    amount_studies = fields.Monetary(string=u"Montant des études", currency_field='currency_id')
    amount_engaged = fields.Monetary(string=u"Montant engagé", currency_field='currency_id')
    amount_current = fields.Monetary(string=u"Montant sit. en cours", currency_field='currency_id')
    amount_invoiced = fields.Monetary(string=u"Montant facturé", currency_field='currency_id')
    amount_final = fields.Monetary(string=u"Montant sit. finale", currency_field='currency_id')

    amount_init_pct = fields.Monetary(string=u"Montant initial (%)")
    amount_compl_pct = fields.Monetary(string=u"Montant complémentaire (%)")
    amount_studies_pct = fields.Monetary(string=u"Montant des études (%)")
    amount_engaged_pct = fields.Monetary(string=u"Montant engagé (%)")
    amount_current_pct = fields.Monetary(string=u"Montant sit. en cours (%)")
    amount_invoiced_pct = fields.Monetary(string=u"Montant facturé (%)")
    amount_final_pct = fields.Monetary(string=u"Montant sit. finale (%)")
