# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.of_utils.models.of_utils import format_date


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    # Horaires web
    of_website_segment_ids = fields.One2many(
        comodel_name='of.horaire.segment', inverse_name='employee_id', string=u"Horaires web",
        domain=[('type', '=', 'website')])
    of_website_hours_summary = fields.Html(
        compute='_compute_of_website_hours_summary', string=u"Récapitulatif horaires web")

    @api.depends('of_website_segment_ids')
    def _compute_of_website_hours_summary(self):

        def formate_segment(segment):
            return '<p>\n&nbsp;&nbsp;&nbsp;' + '<br/>\n&nbsp;&nbsp;&nbsp;'.join(segment.format_str_list()) + '</p>\n'

        segment_obj = self.env['of.horaire.segment']
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        today = fields.Date.today()

        for employee in self:
            segments_temp = segment_obj.search([
                ('employee_id', '=', employee.id),
                ('permanent', '=', False),
                ('date_fin', '>=', today),
                ('type', '=', 'website')])
            segments_perm = segment_obj.search([
                ('employee_id', '=', employee.id),
                ('permanent', '=', True),
                ('type', '=', 'website')], order="date_deb")

            summary = u"<p><i class='oe_grey'>Les horaires web passés ne sont pas affichés.</i></p>"
            if segments_perm:
                segments_perm_futur = segments_perm.filtered(lambda s: s.date_deb > today)
                segments_perm_passe = (segments_perm - segments_perm_futur)
                segment_perm_cur = segments_perm_passe[-1]

                if segment_perm_cur.date_deb != "1970-01-01":
                    depuis_cur = u"le " + format_date(segment_perm_cur.date_deb, lang)
                else:
                    depuis_cur = u""
                if segment_perm_cur.motif:
                    depuis_cur += u"(%s)" % segment_perm_cur.motif

                summary += u'<h3>Horaires web depuis %s</h3>\n<p>\n%s</p>\n' % \
                    (depuis_cur, formate_segment(segment_perm_cur))

                for seg in segments_perm_futur:
                    summary += u"<h3>Changement d'horaires web à partir du " + format_date(seg.date_deb, lang)
                    if seg.motif:
                        summary += u" (%s)" % seg.motif
                    summary += u'</h3>\n<p>\n' + formate_segment(seg) + u'</p>\n'
            else:
                summary = u"<p><b class='of_red'><i class='fa fa-lg fa-warning'/>" \
                    u"Aucun horaire web permanent n'est renseigné</b></p>"
            if segments_temp:
                summary += u"<h3>Horaires web temporaires à venir</h3>\n"
                for seg in segments_temp:
                    if seg.date_deb == seg.date_fin:
                        summary += u"<h5>Le " + format_date(seg.date_deb, lang)
                    else:
                        summary += u"<h5>du %s au %s" % \
                            (format_date(seg.date_deb, lang), format_date(seg.date_fin, lang))
                    if seg.motif:
                        summary += u" (%s)" % seg.motif
                    summary += u'</h5>\n<p>\n' + formate_segment(seg) + u'</p>\n'
            employee.of_website_hours_summary = summary


class OFHoraireSegment(models.Model):
    _inherit = 'of.horaire.segment'

    type = fields.Selection(selection_add=[('website', u"Web")])
