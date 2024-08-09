# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFContractTemplateLine(models.Model):
    _name = 'of.contract.template.line'

    name = fields.Char(string=u"Libellé", required=True)
    contract_tmpl_id = fields.Many2one(comodel_name='of.contract.template', string=u"Modèle de contrat")

    # Planification
    intervention_template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template', string=u"Modèle d'intervention"
    )
    task_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche", required=True)
    interv_frequency_nbr = fields.Integer(string=u"Interval de fréquence (RDV)", required=True)
    interv_frequency = fields.Selection(
        selection=[
            ('month', u"Mois"),
            ('year', u"Ans"),
        ],
        string=u"Type de fréquence (RDV)",
        required=True,
    )
    month_reference_ids = fields.Many2many(comodel_name='of.mois', string=u"Mois de visite", required=True)
    notes = fields.Text(string=u"Notes")
    use_sav = fields.Boolean(string=u"Utilise les SAV")
    sav_count = fields.Integer(string=u"Nombre de visites SAV")

    # Facturation
    display_invoicing = fields.Boolean(string=u"Détails facturation")
    frequency_type = fields.Selection(
        [
            ('date', u"À la prestation"),
            ('month', u"Mensuelle"),
            ('trimester', u"Trimestrielle"),  # Tout les 3 mois
            ('semester', u"Semestrielle"),  # 2 fois par ans
            ('year', u"Annuelle"),
        ],
        string=u"Fréquence de facturation",
        required=True,
    )
    recurring_invoicing_payment_id = fields.Many2one(
        comodel_name='of.contract.recurring.invoicing.payment',
        string=u"Type de facturation",
        required=True,
    )
    grouped = fields.Boolean(string=u"Regrouper la facturation")
    contract_product_ids = fields.One2many(
        comodel_name='of.contract.template.product', inverse_name='line_id', string=u"Lignes d'articles"
    )

    @api.onchange('intervention_template_id')
    def _onchange_intervention_template_id(self):
        self.task_id = self.intervention_template_id.tache_id

    @api.onchange('frequency_type')
    def _onchange_frequency_type(self):
        self.ensure_one()
        if self.frequency_type == 'date':
            if self.recurring_invoicing_payment_id.code not in ('date', 'post-paid'):
                self.recurring_invoicing_payment_id = False
        elif self.frequency_type:
            if self.recurring_invoicing_payment_id.code not in ('pre-paid', 'post-paid'):
                self.recurring_invoicing_payment_id = False

    @api.multi
    def get_contract_line_vals(self):
        self.ensure_one()
        return {
            'state': 'draft',
            'type': 'initial',
            'contract_product_ids': [
                (
                    0,
                    0,
                    p.get_contract_product_vals()
                )
                for p in self.contract_product_ids
            ],
            'intervention_template_id': self.intervention_template_id.id,
            'tache_id': self.task_id.id,
            'interv_frequency_nbr': self.interv_frequency_nbr,
            'interv_frequency': self.interv_frequency,
            'mois_reference_ids': [(4, month_id) for month_id in self.month_reference_ids.ids],
            'notes': self.notes,
            'use_sav': self.use_sav,
            'sav_count': self.sav_count,
            'afficher_facturation': self.display_invoicing,
            'frequency_type': self.frequency_type,
            'recurring_invoicing_payment_id': self.recurring_invoicing_payment_id.id,
            'grouped': self.grouped,
        }
