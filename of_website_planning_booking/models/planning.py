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

    @api.multi
    def get_website_name(self):
        # Called from website so user might not have all access necessary
        self_sudo = self.sudo()
        names = [
            self_sudo.product_id.name,
            self_sudo.name or u"N° de série non renseigné"
        ]
        return u" - ".join(names)


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
        comodel_name='of.jours', relation='of_planning_tache_jours_rel', column1='tache_id', column2='jour_id',
        string=u"Jours à planifier", default=lambda self: self._default_jours_ids())

    def _default_jours_ids(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order='numero')
        res = [(4, jour.id) for jour in jours]
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

    @api.multi
    def get_price_ttc(self):
        self.ensure_one()
        company = self.env.user.company_id
        product = self.sudo().product_id
        price = product.list_price
        taxes = self.sudo().fiscal_position_id.default_tax_ids.compute_all(price, company.currency_id, 1,
                                                                           product=product,
                                                                           partner=self.env.user.partner_id)
        return taxes['total_included']


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
