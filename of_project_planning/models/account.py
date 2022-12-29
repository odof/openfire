# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountAnalyticLine(models.Model):
    u"""Activités de feuille de temps"""
    _inherit = 'account.analytic.line'

    of_planned_activity_id = fields.Many2one(comodel_name='of.project.task.planning', string=u"Activité planifiée")

    @api.onchange('date', 'user_id', 'task_id')
    def _onchange_period_params(self):
        self.ensure_one()
        if self.date and self.user_id and self.task_id:
            # Y a-t-il une activité planifiée pour cet utilisateur pour cette tâche à cette date ?
            planned_activities = self.task_id.of_planning_ids.filtered(
                lambda p:
                p.user_id.id == self.user_id.id and p.period_id.premier_jour <= self.date <= p.period_id.dernier_jour)
            if planned_activities:
                self.of_planned_activity_id = planned_activities[0].id
            else:
                self.of_planned_activity_id = False
