# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

from datetime import timedelta


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    of_state = fields.Selection(selection=[
        ('draft', u"Brouillon"),
        ('done', u"Validé")], string=u"État", readonly=True, required=True, default='done')
    of_real_startdate = fields.Datetime(string=u"Date de début réelle")
    of_real_enddate = fields.Datetime(string=u"Date de fin réelle")
    of_real_duration = fields.Float(
        string=u"Durée réelle", compute='_compute_of_real_duration', inverse='_set_of_real_duration')
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
    of_user_ids = fields.Many2many(
        comodel_name='res.users', relation='of_analytic_line_res_users_rel', column1='analytic_line_id',
        column2='user_id', compute='_compute_of_user_ids', string=u'Utilisateurs')

    @api.depends('of_intervention_id', 'of_intervention_id.employee_ids')
    def _compute_of_user_ids(self):
        for line in self:
            if line.of_intervention_id and line.of_intervention_id.employee_ids:
                users = line.of_intervention_id.employee_ids.mapped('user_id') \
                        - line.of_intervention_id.of_analytic_line_ids.mapped('user_id')
                line.of_user_ids = [(6, 0, users.ids)]
            else:
                line.of_user_ids = False

    @api.depends('of_real_startdate', 'of_real_enddate', 'of_break_duration', 'of_trip_duration')
    def _compute_of_real_duration(self):
        for line in self:
            if line.of_real_startdate and line.of_real_enddate:
                diff = fields.Datetime.from_string(
                    line.of_real_enddate) - fields.Datetime.from_string(line.of_real_startdate)
                break_trip_duration = line.of_break_duration + line.of_trip_duration
                line.of_real_duration = round(diff.total_seconds() / 3600.0, 2) - break_trip_duration
            else:
                line.of_real_duration = 0.0

    @api.depends('of_real_duration', 'of_real_enddate', 'of_break_duration', 'of_trip_duration')
    def _set_of_real_duration(self):
        for line in self:
            if line.of_real_enddate and line.of_real_duration:
                break_trip_duration = line.of_break_duration + line.of_trip_duration
                total_duration = line.of_real_duration + break_trip_duration
                line.of_real_startdate = \
                    fields.Datetime.from_string(line.of_real_enddate) - timedelta(hours=total_duration)
            else:
                line.of_real_startdate = False

    @api.onchange('of_intervention_id')
    def _onchange_of_intervention_id(self):
        if self.of_intervention_id:
            self.name = self.of_intervention_id.name

    @api.onchange('of_real_startdate')
    def _onchange_of_real_startdate(self):
        if self.of_real_startdate:
            self.date = self.of_real_startdate
