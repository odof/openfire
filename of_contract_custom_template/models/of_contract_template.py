# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFContractTemplate(models.Model):
    _name = 'of.contract.template'

    name = fields.Char(string=u"Libellé", required=True)

    # Facturation
    contract_type = fields.Selection(
        [
            ('simple', u"Simple"),
            ('advanced', u"Avancé"),
        ],
        string=u"Type de contrat",
        default='simple',
    )
    recurring_rule_type = fields.Selection(
        [
            ('date', u"À la prestation"),
            ('month', u"Mensuelle"),
            ('trimester', u"Trimestrielle"),  # Tout les 3 mois
            ('semester', u"Semestrielle"),  # 2 fois par ans
            ('year', u"Annuelle"),
        ],
        string=u"Fréquence de facturation",
        help=u"Intervalle de temps entre chaque facturation",
        required=True,
        default='month',
    )
    recurring_invoicing_payment_id = fields.Many2one(
        comodel_name='of.contract.recurring.invoicing.payment', string=u"Type de facturation", required=True,
        default=lambda s: s.env.ref(
            'of_contract_custom.of_contract_recurring_invoicing_payment_pre-paid', raise_if_not_found=False
        ),
    )
    property_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string=u"Journal",
        default=lambda s: s._default_journal(),
        domain="[('type', '=', 'sale')]",
        company_dependent=True,
    )
    property_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string=u"Position fiscale", company_dependent=True,)
    payment_term_id = fields.Many2one(comodel_name='account.payment.term', string=u"Conditions de règlement")
    grouped = fields.Boolean(string=u"Regrouper la facturation")
    revision = fields.Selection(
        [
            ('none', u"Aucune"),
            ('last_day', u"Dernier jour du contrat"),
        ],
        string=u"Période de révision",
        default='last_day',
    )

    # Renouvellement
    renewal = fields.Boolean(string=u"Renouvellement automatique", default=True)
    use_index = fields.Boolean(string=u"Indexer")

    # Lignes
    line_ids = fields.One2many(
        comodel_name='of.contract.template.line', inverse_name='contract_tmpl_id', string=u"Lignes de contrat"
    )

    @api.onchange('recurring_rule_type')
    def _onchange_recurring_rule_type(self):
        if self.recurring_rule_type == 'date':
            if self.recurring_invoicing_payment_id.code not in ('date', 'post-paid'):
                self.recurring_invoicing_payment_id = False
        elif self.recurring_rule_type:
            if self.recurring_invoicing_payment_id.code not in ('pre-paid', 'post-paid'):
                self.recurring_invoicing_payment_id = False

    @api.onchange('contract_type')
    def _onchange_contract_type(self):
        if self.contract_type == 'simple':
            self.grouped = True
            self.revision = 'none'

    @api.multi
    def get_contract_vals(self):
        self.ensure_one()
        return {
            'contract_type': self.contract_type,
            'contract_tmpl_id': self.id,
            'recurring_invoicing_payment_id': self.recurring_invoicing_payment_id.id,
            'recurring_rule_type': self.recurring_rule_type,
            'payment_term_id': self.payment_term_id.id,
            'grouped': self.grouped,
            'revision': self.revision,
            'renewal': self.renewal,
            'use_index': self.use_index,
            'fiscal_position_id': self.property_fiscal_position_id.id,
            'journal_id': self.property_journal_id.id,
        }
