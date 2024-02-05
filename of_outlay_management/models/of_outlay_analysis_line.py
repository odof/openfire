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

    analysis_id = fields.Many2one(
        comodel_name='of.outlay.analysis', string=u"Analyse de débours", required=True, ondelete='cascade')
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='analysis_id.currency_id', string=u"Devise", readonly=True
    )
    analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")
    type = fields.Selection(selection=OUTLAY_LINE_TYPES, string=u"Type", required=True)
    is_closed = fields.Boolean(string=u"Clôturé")

    amount_init = fields.Monetary(string=u"Montant initial", currency_field='currency_id')
    amount_compl = fields.Monetary(string=u"Montant complémentaire", currency_field='currency_id')
    amount_studies = fields.Monetary(string=u"Montant des études", currency_field='currency_id')
    amount_engaged = fields.Monetary(string=u"Montant engagé", currency_field='currency_id')
    amount_current = fields.Monetary(string=u"Montant sit. en cours", currency_field='currency_id')
    amount_invoiced = fields.Monetary(string=u"Montant facturé", currency_field='currency_id')
    amount_final = fields.Monetary(string=u"Montant sit. finale", currency_field='currency_id')

    amount_init_pct = fields.Float(string=u"Montant initial (%)")
    amount_compl_pct = fields.Float(string=u"Montant complémentaire (%)")
    amount_studies_pct = fields.Float(string=u"Montant des études (%)")
    amount_engaged_pct = fields.Float(string=u"Montant engagé (%)")
    amount_current_pct = fields.Float(string=u"Montant sit. en cours (%)")
    amount_invoiced_pct = fields.Float(string=u"Montant facturé (%)")
    amount_final_pct = fields.Float(string=u"Montant sit. finale (%)")
    progress_pct = fields.Float(string=u"Avancement (%)")

    @api.onchange('amount_init_pct')
    def _onchange_amount_init_pct(self):
        self.recompute_amount(self._origin.analysis_id)

    @api.multi
    def write(self, vals):
        res = super(OFOutlayAnalysisLine, self).write(vals)
        if len(self) == 1 and self.type == 'margin_objective' and 'amount_init_pct' in vals:
            analysis = self.analysis_id
            lang = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'fr_FR'))])
            currency = analysis.currency_id

            # Recalcul des montants en fonction des nouveaux pourcentages
            self.recompute_amount(analysis)

            # Recalcul des valeurs kanban
            kanban_categories = {
                'amount_init': '01_initial',
                'amount_compl': '02_complementary',
                'amount_engaged': '03_involved',
                'amount_current': '04_current',
                'amount_invoiced': '05_invoiced',
            }
            margin_lines = analysis.line_ids.filtered(lambda line: line.type == 'margin_objective')
            income_lines = analysis.line_ids.filtered(lambda line: line.type == 'income')
            margin_kanban = analysis.kanban_record_ids.filtered(lambda k: k.type == '03_gross_margin')
            for field, category in kanban_categories.iteritems():
                total_margin = sum(margin_lines.mapped(field))
                total_income = sum(income_lines.mapped(field))
                margin_kanban.filtered(lambda k: k.category == category).write({
                    'value2':
                        margin_kanban.format_number(total_income and 100 * total_margin / total_income, lang)
                        + u" %",
                    'value4': margin_kanban.format_number(total_margin, lang, currency=currency),
                })
        return res

    @api.multi
    def action_close(self):
        self._set_is_closed(True)

    @api.multi
    def action_open(self):
        self._set_is_closed(False)

    @api.model
    def _fields_to_recompute(self):
        return [
            'amount_init', 'amount_compl', 'amount_studies', 'amount_engaged',
            'amount_current', 'amount_invoiced', 'amount_final',
        ]

    @api.multi
    def recompute_amount(self, analysis):
        if self.type != 'margin_objective':
            return
        for line in analysis.line_ids:
            if line.type == 'income' and line.analytic_section_id == self.analytic_section_id:
                break
        else:
            # Ligne de produit non trouvée
            return
        amount_pct = self.amount_init_pct
        vals_dict = {
            field_name: line[field_name] * amount_pct / 100.0
            for field_name in self._fields_to_recompute()
        }
        vals_dict.update({
            key + '_pct': amount_pct
            for key in vals_dict
        })
        del vals_dict['amount_init_pct']
        self.update(vals_dict)

    @api.multi
    def _set_is_closed(self, is_closed):
        all_lines = self.env['of.outlay.analysis.line']
        for line in self:
            all_lines |= line.analysis_id.line_ids.filtered(
                lambda line: line.analytic_section_id == line.analytic_section_id
            )
        all_lines.write({'is_closed': is_closed})
