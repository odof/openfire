# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons.of_utils.models.of_utils import format_date


class OFCalculationStatistics(models.Model):
    _name = 'of.calculation.statistics'
    _order = 'date DESC'

    name = fields.Char(string=u"Nom", compute='_compute_name')
    date = fields.Date(string=u"Date", required=True)
    button_reload = fields.Integer(string=u"Clics Nouveau calcul")
    button_validate = fields.Integer(string=u"Clics Valider")
    button_mail = fields.Integer(string=u"Clics Envoyer")

    @api.depends('date')
    def _compute_name(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for record in self:
            record.name = 'Statistiques du %s' % format_date(record.date, lang, with_year=False)

    @api.model
    def add_button_click(self, button):
        button_field = 'button_' + button
        calculation_statistics_obj = self.env['of.calculation.statistics']
        if button_field not in self._fields:
            return
        record = calculation_statistics_obj.search([('date', '=', fields.Date.today())])
        if not record:
            record = calculation_statistics_obj.create({'date': fields.Date.today()})
        record.write({button_field: record[button_field] + 1})
