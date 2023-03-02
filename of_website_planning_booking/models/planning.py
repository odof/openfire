# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.of_utils.models.of_utils import format_date
from odoo.exceptions import ValidationError, UserError


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    annee_batiment = fields.Char(string=u"Année de construction du bâtiment")
    website_create = fields.Boolean(string=u"Créé par le portail web")
    website_extra_brand = fields.Char(string=u"Autre marque du portail web")
    website_installer_name = fields.Char(string=u"Nom de l'installateur du portail web")
    website_installer_email = fields.Char(string=u"E-mail de l'installateur du portail web")


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    website_create = fields.Boolean(string=u"Créé par le portail web")


class OFPlanningTache(models.Model):
    _inherit = 'of.planning.tache'

    modele_id = fields.Many2one(comodel_name='of.horaire.modele', string=u"Charger un modèle")
    mode_horaires = fields.Selection(selection=[
        ('easy', u"Facile"),
        ('advanced', u"Avancé")], string=u"Mode de Sélection des créneaux", required=True, default='easy')
    creneau_ids = fields.Many2many(comodel_name='of.horaire.creneau', string=u"Créneaux")
    segment_ids = fields.One2many(
        comodel_name='of.horaire.segment', inverse_name='tache_id', string=u"Horaires de planification",
        domain=[('type', '=', 'regular')])
    horaire_recap = fields.Html(compute='_compute_horaire_recap', string=u"Horaires de planification")
    hor_md = fields.Float(string=u"Matin début", digits=(12, 5), default=9)
    hor_mf = fields.Float(string=u"Matin fin", digits=(12, 5), default=12)
    hor_ad = fields.Float(string=u"Après-midi début", digits=(12, 5), default=14)
    hor_af = fields.Float(string=u"Après-midi fin", digits=(12, 5), default=18)
    jour_ids = fields.Many2many(
        comodel_name='of.jours', string=u"Jours à planifier", default=lambda self: self._default_jours_ids())

    def _default_jours_ids(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order='numero')
        res = [jour.id for jour in jours]
        return res

    @api.depends('segment_ids')
    def _compute_horaire_recap(self):
        def formate_segment(segment):
            return u"<p>\n&nbsp;&nbsp;&nbsp;" + u"<br/>\n&nbsp;&nbsp;&nbsp;".join(segment.format_str_list()) + u"</p>\n"
        for tache in self:
            segments_perm = tache.segment_ids
            if segments_perm:
                recap = u"<h3>Créneaux disponibles </h3>\n<p>\n%s</p>\n" % (formate_segment(segments_perm))
            else:
                recap = u"<p><b class='of_red'><i class='fa fa-lg fa-warning'/> Aucun créneau n'est renseigné.</b></p>"
            tache.horaire_recap = recap

    @api.onchange('modele_id')
    def onchange_modele_id(self):
        self.ensure_one()
        if self.modele_id:
            self.creneau_ids = self.modele_id.creneau_ids.ids
            self.mode_horaires = 'advanced'
            self.modele_id = False

    @api.multi
    @api.onchange('hor_md', 'hor_mf', 'hor_ad', 'hor_af', 'mode_horaires')
    def onchange_hor_ma_df(self):
        self.ensure_one()
        if self.mode_horaires == 'easy' and not (0 <= self.hor_md <= self.hor_mf <= self.hor_ad <= self.hor_af < 24):
            raise UserError(u"Il y a une incohérence au niveau des horaires des créneaux.")

    @api.multi
    def button_new_booking_schedule(self):
        # adapté de button_create_edit() de openfire/of_calendar/models/of_calendar.py pour fonctionnement sur tache
        self.ensure_one()
        self.onchange_hor_ma_df()
        creneau_obj = self.env['of.horaire.creneau']
        segment_obj = self.env['of.horaire.segment']
        if self.mode_horaires == 'easy':
            create_exist_ids = creneau_obj.create_if_necessary(
                self.hor_md, self.hor_mf, self.hor_ad, self.hor_af, self.jour_ids.ids)
            creneau_ids = create_exist_ids['create_ids'] + create_exist_ids['exist_ids']
        else:
            creneau_ids = self.creneau_ids.ids

        self.remplacement = False
        vals = {
            'tache_id': self.id,
            'creneau_ids': [(6, 0, creneau_ids)],
        }
        vals['date_deb'] = '1970-01-01'
        vals['permanent'] = True
        vals['type'] = 'regular'
        self.segment_ids.unlink()
        segment_obj.create(vals)
        return {'type': 'ir.actions.do_nothing'}



class HREmployee(models.Model):
    _inherit = 'hr.employee'

    # Horaires web
    of_website_booking_segment_ids = fields.One2many(
        comodel_name='of.horaire.segment', inverse_name='employee_id', string=u"Horaires web",
        domain=[('type', '=', 'website')])
    of_website_booking_horaire_recap = fields.Html(
        compute='_compute_of_website_booking_horaire_recap', string=u"Horaires web")

    @api.depends('of_website_booking_segment_ids')
    def _compute_of_website_booking_horaire_recap(self):

        def formate_segment(segment):
            return '<p>\n&nbsp;&nbsp;&nbsp;' + '<br/>\n&nbsp;&nbsp;&nbsp;'.join(segment.format_str_list()) + '</p>\n'

        segment_obj = self.env['of.horaire.segment']
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        date_str = fields.Date.today()

        for employee in self:
            segments_temp = segment_obj.search([
                ('employee_id', '=', employee.id),
                ('permanent', '=', False),
                ('date_fin', '>=', date_str),
                ('type', '=', 'website')])
            segments_perm = segment_obj.search([
                ('employee_id', '=', employee.id),
                ('permanent', '=', True),
                ('type', '=', 'website')], order="date_deb")

            recap = u"<p><i class='oe_grey'>Les horaires web passés ne sont pas affichés.</i></p>"
            if segments_perm:
                segments_perm_futur = segments_perm.filtered(lambda s: s.date_deb > date_str)
                segments_perm_passe = (segments_perm - segments_perm_futur)
                segment_perm_cur = segments_perm_passe[-1]

                if segment_perm_cur.date_deb != "1970-01-01":
                    depuis_cur = u"le " + format_date(segment_perm_cur.date_deb, lang)
                else:
                    depuis_cur = u""
                if segment_perm_cur.motif:
                    depuis_cur += u"(%s)" % segment_perm_cur.motif

                recap += u'<h3>Horaires web depuis %s</h3>\n<p>\n%s</p>\n' % (depuis_cur, formate_segment(segment_perm_cur))

                for seg in segments_perm_futur:
                    recap += u"<h3>Changement d'horaires web à partir du " + format_date(seg.date_deb, lang)
                    if seg.motif:
                        recap += u" (%s)" % seg.motif
                    recap += u'</h3>\n<p>\n' + formate_segment(seg) + u'</p>\n'
            else:
                recap = u"<p><b class='of_red'><i class='fa fa-lg fa-warning'/>" \
                        u"Aucun horaire web permanent n'est renseigné</b></p>"
            if segments_temp:
                recap += u"<h3>Horaires web temporaires à venir</h3>\n"
                for seg in segments_temp:
                    if seg.date_deb == seg.date_fin:
                        recap += u"<h5>Le " + format_date(seg.date_deb, lang)
                    else:
                        recap += u"<h5>du %s au %s" % (format_date(seg.date_deb, lang),
                                                       format_date(seg.date_fin, lang))
                    if seg.motif:
                        recap += u" (%s)" % seg.motif
                    recap += u'</h5>\n<p>\n' + formate_segment(seg) + u'</p>\n'
            employee.of_website_booking_horaire_recap = recap


class OFHoraireSegment(models.Model):
    _inherit = 'of.horaire.segment'

    type = fields.Selection(selection_add=[('website', u"Web")])


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model
    def _auto_init(self):
        super(OFInterventionSettings, self)._auto_init()
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_allowed_month_ids') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'website_booking_allowed_month_ids', self._default_allowed_month_ids())
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_allowed_day_ids') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'website_booking_allowed_day_ids', self._default_allowed_day_ids())
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_open_days_number') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_booking_open_days_number', 60)
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_allow_empty_days') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_booking_allow_empty_days', True)
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_slot_size') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_booking_slot_size', 'half_day')

    def _default_website(self):
        return self.env['website'].search([], limit=1)

    def _default_allowed_month_ids(self):
        months = self.env['of.mois'].search([], order='numero')
        res = [month.id for month in months]
        return res

    def _default_allowed_day_ids(self):
        days = self.env['of.jours'].search([('numero', '<', 6)], order='numero')
        res = [day.id for day in days]
        return res

    website_booking_allowed_month_ids = fields.Many2many(
        comodel_name='of.mois', string=u"(OF) Mois ouverts", default=_default_allowed_month_ids)
    website_booking_allowed_day_ids = fields.Many2many(
        comodel_name='of.jours', string=u"(OF) Jours ouverts", default=_default_allowed_day_ids)
    website_booking_allowed_employee_ids = fields.Many2many(
        comodel_name='hr.employee', relation='of_intervention_settings_web_allowed_employee_rel',
        column1='of_intervention_settings_id', column2='employee_id', string=u"(OF) Techniciens disponibles",
        domain=[('of_est_intervenant', '=', True)])
    website_booking_open_days_number = fields.Integer(
        string=u"(OF) Nombre de jours ouverts à la réservation (max 180 jours)", default=60)
    website_booking_allow_empty_days = fields.Boolean(
        string=u"(OF) Autorise la réservation de créneau sur des journées vierges", default=True)
    website_booking_slot_size = fields.Selection(
        selection=[('half_day', u"Demi-journée"), ('manual', u"Manuelle")], string=u"(OF) Granularité de réservation",
        default='half_day', required=True)
    group_website_booking_allow_park_creation = fields.Boolean(
        string=u"(OF) Création de parcs",
        implied_group='of_website_planning_booking.group_website_booking_allow_park_creation',
        group='base.group_portal,base.group_user,base.group_public',
        help=u"Autorise la création des parcs installés extérieurs")
    group_website_booking_allow_park_brand_creation = fields.Boolean(
        string=u"(OF) Ajout de marques",
        implied_group='of_website_planning_booking.group_website_booking_allow_park_brand_creation',
        group='base.group_portal,base.group_user,base.group_public',
        help=u"Autorise la création des parcs installés sur des marques extérieures")
    website_booking_default_product_brand_id = fields.Many2one(
        comodel_name='of.product.brand', string=u"(OF) Marque des parcs",
        help=u"Marque utilisée pour la création des parcs installés",
        default=lambda self: self.env['ir.model.data'].xmlid_to_object(
            'of_website_planning_booking.of_website_planning_booking_brand_default'))
    website_id = fields.Many2one(comodel_name='website', string=u"Site web", default=_default_website, required=True)
    website_booking_terms_file = fields.Binary(
        related='website_id.website_booking_terms_file', string=u"(OF) Fichier PDF des Conditions Générales de Vente",
        filename='website_booking_terms_filename')
    website_booking_terms_filename = fields.Char(
        related='website_id.website_booking_terms_filename',
        string=u"(OF) Nom du fichier PDF des Conditions Générales de Vente")

    @api.constrains('website_booking_open_days_number')
    def _check_website_booking_open_days_number_constaint(self):
        for record in self:
            if record.website_booking_open_days_number < 0:
                raise ValidationError(u"Vous ne pouvez pas avoir un nombre de jours ouverts à la réservation négatif.")
            if record.website_booking_open_days_number > 180:
                raise ValidationError(u"Vous ne pouvez pas avoir un nombre de jours ouverts à la réservation supérieur "
                                      u"à 180.")

    @api.multi
    def set_website_booking_allowed_month_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allowed_month_ids', self.website_booking_allowed_month_ids.ids)

    @api.multi
    def set_website_booking_allowed_day_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allowed_day_ids', self.website_booking_allowed_day_ids.ids)

    @api.multi
    def set_website_booking_allowed_employee_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allowed_employee_ids',
            self.website_booking_allowed_employee_ids.ids)

    @api.multi
    def set_website_booking_open_days_number_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_open_days_number', self.website_booking_open_days_number)

    @api.multi
    def set_website_booking_allow_empty_days_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allow_empty_days', self.website_booking_allow_empty_days)

    @api.multi
    def set_website_booking_slot_size_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_slot_size', self.website_booking_slot_size)

    @api.multi
    def set_website_booking_default_product_brand_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_default_product_brand_id',
            self.website_booking_default_product_brand_id.id)

    @api.onchange('group_website_booking_allow_park_creation')
    def _onchange_group_website_booking_allow_park_creation(self):
        self.ensure_one()
        if not self.group_website_booking_allow_park_creation:
            self.group_website_booking_allow_park_brand_creation = False
