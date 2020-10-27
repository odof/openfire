# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMoveTemplate(models.Model):
    _inherit = 'account.move.template'

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
        help=u"L'année sera automatiquement recalculée dans l'outil de crétion des pièces comptables.")
