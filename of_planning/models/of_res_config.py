# -*- coding: utf-8 -*-

from odoo import models, fields

class OfInterventionSettings(models.TransientModel):
    _name = 'of.intervention.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(
        'res.company', string='(OF) Société', required=True,
        default=lambda self: self.env.user.company_id)

    calendar_min_time = fields.Integer(string='(OF) Heure min', help="Heure minimale affichée")
    calendar_max_time = fields.Integer(string='(OF) Heure max', help="Heure maximale affichée")

    color_dispo_ft = fields.Char(string="(OF) créneaux dispo", help=u"Couleur de texte des créneaux disponibles.", default="#0C0C0C")
    color_dispo_bg = fields.Char(string="(OF) créneaux dispo", help=u"Couleur de fond des créneaux disponibles.", default="#7FFF00")
    color_indispo_ft = fields.Char(string="(OF) créneaux indispo", help=u"Couleur de texte des créneaux indisponibles.", default="#0C0C0C")
    color_indispo_bg = fields.Char(string="(OF) créneaux indispo", help=u"Couleur de fond des créneaux indisponibles", default="#FF2222")
