# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_revendeur = fields.Boolean(string=u"Revendeur", help=u"Cocher cette case si ce partenaire est un revendeur.")
    of_installateur = fields.Boolean(
        string=u"Installateur", help=u"Cocher cette case si ce partenaire est un installateur.")
    of_parc_installe_count = fields.Integer(string=u"Parc installé", compute='_compute_of_parc_installe_count')
    of_parc_installe_ids = fields.One2many(
        comodel_name='of.parc.installe', inverse_name='client_id', string=u"Parc installé")

    @api.multi
    def _compute_of_parc_installe_count(self):
        for partner in self:
            partner.of_parc_installe_count = self.env['of.parc.installe'].search_count([('client_id', '=', partner.id)])

    @api.multi
    def name_get(self):
        """
        Permet, dans un parc installé ou un pop-up de création de parc installé, de proposer les partenaires
        qui ne sont pas revendeurs/installateurs entre parenthèse. """
        revendeur_prio = self._context.get('of_revendeur_prio')
        installateur_prio = self._context.get('of_installateur_prio')
        if revendeur_prio or installateur_prio:
            result = []
            for employee in self:
                est_prio = revendeur_prio and employee.of_revendeur or installateur_prio and employee.of_installateur
                result.append((employee.id, "%s%s%s" % ('' if est_prio else '(',
                                                        employee.name,
                                                        '' if est_prio else ')')))
            return result
        return super(ResPartner, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un parc installé de proposer en premier les partenaires revendeurs/installateurs"""
        champ_prio = ''
        if self._context.get('of_revendeur_prio'):
            champ_prio = 'of_revendeur'
        elif self._context.get('of_installateur_prio'):
            champ_prio = 'of_installateur'
        if champ_prio:
            args = args or []
            res = super(ResPartner, self).name_search(
                name,
                args + [[champ_prio, '=', True]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(ResPartner, self).name_search(
                name,
                args + [[champ_prio, '=', False]],
                operator,
                limit) or []
            return res
        return super(ResPartner, self).name_search(name, args, operator, limit)
