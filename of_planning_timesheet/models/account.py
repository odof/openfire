# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    of_state = fields.Selection(selection=[
        ('draft', u"Brouillon"),
        ('done', u"Validé")], string=u"État", readonly=True, required=True, default='done')
    of_real_startdate = fields.Datetime(string=u"Date de début réelle")
    of_real_enddate = fields.Datetime(string=u"Date de fin réelle")
    of_real_duration = fields.Float(string=u"Durée réelle", compute='_compute_of_real_duration')
    of_intervention_id = fields.Many2one(
        comodel_name='of.planning.intervention', string=u"RDV d'intervention", readonly=True)
    of_planned_startdate = fields.Datetime(
        string=u"Date de début planifiée", related='of_intervention_id.date', readonly=True)
    of_planned_enddate = fields.Datetime(
        string=u"Date de fin planifiée", related='of_intervention_id.date_deadline', readonly=True)
    of_planned_duration = fields.Float(
        string=u"Durée prévisionnelle", related='of_intervention_id.duree', readonly=True)
    of_break_duration = fields.Float(string=u"Pause")
    of_trip_duration = fields.Float(string=u"Trajet")

    @api.depends('of_real_startdate', 'of_real_enddate', 'of_break_duration', 'of_trip_duration')
    def _compute_of_real_duration(self):
        for intervention in self:
            if intervention.of_real_startdate and intervention.of_real_enddate:
                diff = fields.Datetime.from_string(
                    intervention.of_real_enddate) - fields.Datetime.from_string(intervention.of_real_startdate)
                break_trip_duration = intervention.of_break_duration + intervention.of_trip_duration
                intervention.of_real_duration = round(diff.total_seconds() / 3600.0, 2) - break_trip_duration
            else:
                intervention.of_real_duration = 0.0

    @api.onchange('of_intervention_id')
    def _onchange_of_intervention_id(self):
        if self.of_intervention_id:
            self.name = self.of_intervention_id.name

    @api.onchange('of_real_startdate')
    def _onchange_of_real_startdate(self):
        if self.of_real_startdate:
            self.date = self.of_real_startdate
