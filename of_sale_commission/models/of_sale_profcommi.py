# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError


class OFSaleRegcommi(models.Model):
    _name = "of.sale.regcommi"
    _description = u"Règles de commissions"

    name = fields.Char(string=u"Libellé")
    code = fields.Text(string="Code")

    _sql_constraints = [
        ('name_id_unique', 'unique (name)', u"Le libellé est déjà utilisé !"),
    ]

    @api.model
    def create(self, vals):
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur a le droit de créer des règles !")
        return super(OFSaleRegcommi, self).create(vals)

    @api.multi
    def write(self, vals):
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur a le droit de modifier des règles !")
        return super(OFSaleRegcommi, self).write(vals)


class OFSaleProfcommi(models.Model):
    _name = "of.sale.profcommi"
    _description = "Profils de commissions"

    name = fields.Char(string="Profil")
    taux_commi = fields.Float(string="Taux global", digits=(16, 2), default=4)
    taux_acompte = fields.Float(string="Indice acompte", default=50)
    taux_solde = fields.Float(string=u"Indice règlement", compute='_compute_taux_solde')
    profcommi_line_ids = fields.One2many('of.sale.profcommi.line', 'profcommi_id', string="Commissions")
    user_ids = fields.One2many('res.users', 'of_profcommi_id', string="Utilisateurs", readonly=True)

    @api.depends('taux_acompte')
    def _compute_taux_solde(self):
        for profcommi in self:
            profcommi.taux_solde = 100 - profcommi.taux_acompte

    _sql_constraints = [
        ('name_id_unique', 'unique (name)', u"Le libellé est déjà utilisé !"),
    ]

    @api.multi
    def get_taux_commi(self, line):
        """
        Recupere le taux de commissionnement pour un profil de commission et une ligne
        type definit le type de ligne : 'acompte' pour order_line, 'solde' ou 'avoir' pour invoice_line
        """
        self.ensure_one()
        taux = self.taux_commi
        product = line.product_id  # A utiliser dans les règles de commissionnement (regcommi_id.code)
        cond = False
        for prof_line in self.profcommi_line_ids:
            if prof_line.type == 'commission':
                exec prof_line.regcommi_id.code
                if cond:
                    taux = prof_line.taux_commi
                    break
        return taux


class OFSaleProfcommiLine(models.Model):
    _name = "of.sale.profcommi.line"
    _description = "Ligne de Profil Commissions"
    _order = "type,sequence"

    name = fields.Char(string=u"Libellé", required=True)
    profcommi_id = fields.Many2one('of.sale.profcommi', string="Profil", ondelete='cascade')
    regcommi_id = fields.Many2one('of.sale.regcommi', string=u"Règle", required=True, ondelete='restrict')
    sequence = fields.Integer(string=u"Séquence")
    taux_commi = fields.Float(string="Pourcentage", digits=(16, 2), default=4)
    type = fields.Selection(
        [('commission', "Taux de Commission"), ('acompte', "Premier Versement")], string="Type", required=True,
        default='commission'
    )
