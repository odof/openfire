# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.addons.of_utils.models.of_utils import format_date
from odoo.exceptions import ValidationError


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
