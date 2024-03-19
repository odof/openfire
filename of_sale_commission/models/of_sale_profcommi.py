# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class OFSaleProfcommi(models.Model):
    _name = 'of.sale.profcommi'
    _description = u"Profils de commissions"

    name = fields.Char(string=u"Profil")
    taux_commi = fields.Float(string=u"Taux global", digits=(16, 2), default=4)
    taux_acompte = fields.Float(string=u"Indice acompte", default=50)
    taux_solde = fields.Float(string=u"Indice règlement", compute='_compute_taux_solde')
    profcommi_line_ids = fields.One2many(
        comodel_name='of.sale.profcommi.line', inverse_name='profcommi_id', string=u"Commissions")
    user_ids = fields.One2many(
        comodel_name='res.users', inverse_name='of_profcommi_id', string=u"Utilisateurs", readonly=True)

    @api.depends('taux_acompte')
    def _compute_taux_solde(self):
        for profcommi in self:
            profcommi.taux_solde = 100 - profcommi.taux_acompte

    _sql_constraints = [
        ('name_id_unique', 'unique (name)', u"Le libellé est déjà utilisé !"),
    ]

    @api.multi
    def get_taux_commi(self, line):
        u"""
        Recupere le taux de commissionnement pour un profil de commission et une ligne
        type definit le type de ligne : 'acompte' pour order_line, 'solde' ou 'avoir' pour invoice_line
        """
        self.ensure_one()
        taux = self.taux_commi
        eval_context = {
            'cond': False,
            'line': line,
            'product': line.product_id,
            'self': self,
        }
        for prof_line in self.profcommi_line_ids:
            if prof_line.type == 'commission':
                eval_context['amount'] = prof_line.taux_commi
                safe_eval(prof_line.regcommi_id.code, eval_context, mode="exec", nocopy=True)
                if eval_context['cond']:
                    taux = eval_context['amount']
                    break
        return taux


class OFSaleProfcommiLine(models.Model):
    _name = 'of.sale.profcommi.line'
    _description = "Ligne de Profil Commissions"
    _order = 'type, sequence'

    name = fields.Char(string=u"Libellé", required=True)
    profcommi_id = fields.Many2one(comodel_name='of.sale.profcommi', string=u"Profil", ondelete='cascade')
    regcommi_id = fields.Many2one(comodel_name='of.sale.regcommi', string=u"Règle", required=True, ondelete='restrict')
    sequence = fields.Integer(string=u"Séquence")
    taux_commi = fields.Float(string=u"Pourcentage", digits=(16, 2), default=4)
    type = fields.Selection(
        [('commission', u"Taux de Commission"), ('acompte', u"Premier Versement")], string=u"Type", required=True,
        default='commission'
    )
