# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    of_template_id = fields.Many2one('account.move.template', string=u"Modèle d'origine")


class AccountMoveTemplate(models.Model):
    _inherit = 'account.move.template'

    template_line_ids = fields.One2many(copy=True)
    of_move_ids = fields.One2many('account.move', 'of_template_id', string=u"Pièces comptables")
    of_moves_count = fields.Integer(compute='_compute_of_moves_count', string=u"Nb. Pièces", store=True)
    of_moves_last_date = fields.Date(compute='_compute_of_moves_last_date', string=u"Dernière pièce", store=True)
    of_recurring = fields.Boolean(string=u"Récurrent")
    of_rec_interval = fields.Integer(string=u"Intervalle", default=1, required=True)
    of_rec_interval_type = fields.Selection(
        [('days', u"Jours"), ('months', u"Mois"), ('years', u"Années")],
        string=u"Unité de temps", default='months', required=True)
    of_rec_number = fields.Integer(string=u"Nombre de pièces", default=12, required=True)
    of_prorata = fields.Boolean(
        string="Prorata",
        help=u"Le montant des écritures sera ajusté au prorata du mois sur le premier et le dernier mois.")

    of_extourne = fields.Selection(
        [
            ('none', u"Pas d'extourne"),
            ('first', u"Date de départ"),
            ('last', u"Date de fin"),
            ('custom', u"Date choisie"),
        ],
        string=u"Extourner", default='none', required=True
    )
    of_extourne_date = fields.Date(
        string="Date extourne",
        help=u"L'année sera automatiquement recalculée dans l'outil de création des pièces comptables.")

    @api.depends('of_move_ids')
    def _compute_of_moves_count(self):
        for template in self:
            template.of_moves_count = len(template.of_move_ids)

    @api.depends('of_move_ids.date')
    def _compute_of_moves_last_date(self):
        for template in self:
            template.of_moves_last_date = template.of_move_ids[:1].date

    @api.multi
    def of_action_view_moves(self):
        action = self.env.ref('account.action_move_line_form').read()[0]
        action['domain'] = [('of_template_id', 'in', self.ids)]
        action['context'] = {
            'default_of_template_id': len(self) == 1 and self.id,
        }
        return action
