# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class OfInterventionSettings(models.TransientModel):
    _name = 'of.intervention.settings'
    _inherit = 'res.config.settings'

    @api.model_cr_context
    def _auto_init(self):
        res = super(OfInterventionSettings, self)._auto_init()
        if not self.env['ir.values'].get_default('of.intervention.settings', 'company_choice'):
            self.env['ir.values'].sudo().set_default(
                    'of.intervention.settings', 'company_choice', 'contact')
        return res

    company_id = fields.Many2one(
        'res.company', string=u'(OF) Société', required=True, default=lambda self: self.env.user.company_id)
    calendar_min_time = fields.Integer(string='(OF) Heure min', help=u"Heure minimale affichée")
    calendar_max_time = fields.Integer(string='(OF) Heure max', help=u"Heure maximale affichée")
    color_bg_creneaux_dispo = fields.Char(
        string=u"(OF) Créneaux dispo couleur fond", default="#7FFF00",
        help=u"Choisissez un couleur de fond pour les créneaux dispos")
    color_ft_creneaux_dispo = fields.Char(
        string=u"(OF) Créneaux dispo couleur texte", default="#0C0C0C",
        help=u"Choisissez un couleur de texte pour les créneaux dispos")
    duree_min_creneaux_dispo = fields.Float(
        string=u"(OF) Créneaux dispo durée min", default="1",
        help=u"durée minimale pour qu'un trou dans le planning soit considéré commme un créneau dispo")
    color_bg_creneaux_indispo = fields.Char(
        string=u"(OF) Créneaux indispo couleur fond", default="#FF2222",
        help=u"Choisissez un couleur de fond pour les créneaux dispos")
    color_ft_creneaux_indispo = fields.Char(
        string=u"(OF) Crenéaux indispo couleur texte", default="#0C0C0C",
        help=u"Choisissez un couleur de texte pour les créneaux dispos")

    fiche_intervention_cacher_montant = fields.Boolean(string=u"(OF) Cacher montant restant")
    company_choice = fields.Selection(
        [
            ('contact', u"la société du contact"),
            ('user', u"la société de l'utilisateur"),
        ], string=u"(OF) Création dans", required=True,
        help=u"Pour la création des RDVs, interventions à programmer, SAV et parcs installés."
    )

    @api.multi
    def set_calendar_min_time_defaults(self):
        if not 0 <= self.calendar_min_time < 24:
            raise ValidationError(u"l'heure minimale doit être entre 0 et 24! (et idéalement pas 24...)")
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'calendar_min_time', self.calendar_min_time)

    @api.multi
    def set_calendar_max_time_defaults(self):
        if not 0 <= self.calendar_max_time <= 24:
            raise ValidationError(u"l'heure maximale doit être entre 0 et 24! (et idéalement pas 0...)")
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'calendar_max_time', self.calendar_max_time)

    @api.multi
    def set_color_bg_creneaux_dispo_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'color_bg_creneaux_dispo', self.color_bg_creneaux_dispo)

    @api.multi
    def set_color_ft_creneaux_dispo_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'color_ft_creneaux_dispo', self.color_ft_creneaux_dispo)

    @api.multi
    def set_duree_min_creneaux_dispo_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'duree_min_creneaux_dispo', self.duree_min_creneaux_dispo)

    @api.multi
    def set_color_bg_creneaux_indispo_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'color_bg_creneaux_indispo', self.color_bg_creneaux_indispo)

    @api.multi
    def set_color_ft_creneaux_indispo_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'color_ft_creneaux_indispo', self.color_ft_creneaux_indispo)

    @api.multi
    def set_fiche_intervention_cacher_montant_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'fiche_intervention_cacher_montant', self.fiche_intervention_cacher_montant)

    @api.multi
    def set_company_choice_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'company_choice', self.company_choice)
