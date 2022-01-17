# -*- coding: utf-8 -*-

import json

from odoo import models, fields, api


class Project(models.Model):
    _inherit = 'project.project'

    of_total_planned_hours = fields.Float(string=u"Durée prévue", compute='_compute_time')
    of_total_done_hours = fields.Float(string=u"Durée réalisée", compute='_compute_time')
    of_ressources = fields.Text(string=u"Ressources", compute='_compute_of_ressources')

    @api.depends('task_ids', 'task_ids.planned_hours', 'task_ids.effective_hours')
    def _compute_time(self):
        """
        Calcul les temps consolidés d'un projet en fonction des temps de ses tâches
        """
        for project in self:
            project.of_total_planned_hours = sum(project.task_ids.mapped('planned_hours'))
            project.of_total_done_hours = sum(project.task_ids.mapped('effective_hours'))

    @api.depends('task_ids', 'task_ids.of_planning_ids', 'task_ids.of_planning_ids.user_id')
    def _compute_of_ressources(self):
        for project in self:
            ressources = []
            all_ressources = set(
                project.task_ids.mapped('of_planning_ids').filtered(lambda p: p.user_id).mapped('user_id'))
            for user in all_ressources:
                ressources.append({'id': user.id, 'name': user.name})
            project.of_ressources = json.dumps(ressources) if ressources else False


class ProjectTask(models.Model):
    _inherit = 'project.task'

    planned_hours = fields.Float(compute='_compute_planned_hours', store=True)
    of_gb_period_id = fields.Many2one(
        comodel_name='of.periode.planifiee', compute='lambda *a, **k:{}', search='_search_of_gb_period_id',
        string=u"Période", of_custom_groupby=True)
    of_planning_ids = fields.One2many(
        comodel_name='of.project.task.planning', inverse_name='task_id', string=u"Planification")
    of_ressources = fields.Text(string=u"Ressources", compute='_compute_of_ressources')

    def _search_of_gb_period_id(self, operator, value):
        return [('of_planning_ids.period_id', operator, value)]

    @api.depends('of_planning_ids', 'of_planning_ids.duration')
    def _compute_planned_hours(self):
        for task in self:
            task.planned_hours = sum(task.of_planning_ids.mapped('duration'))

    @api.depends('of_planning_ids', 'of_planning_ids.user_id')
    def _compute_of_ressources(self):
        for task in self:
            ressources = []
            all_ressources = set(task.of_planning_ids.filtered(lambda p: p.user_id).mapped('user_id'))
            for user in all_ressources:
                ressources.append({'id': user.id, 'name': user.name})
            task.of_ressources = json.dumps(ressources) if ressources else False

    @api.onchange('of_planning_ids', 'of_planning_ids.period_id')
    def onchange_of_planning_ids(self):
        """
        Recalcul les dates de début et fin de tâches en fonction de la planification
        """
        if self.of_planning_ids:
            self.date_start = min(self.of_planning_ids.mapped('period_id').mapped('premier_jour'))
            self.date_end = max(self.of_planning_ids.mapped('period_id').mapped('dernier_jour'))

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """Ajout de la possibilité de regrouper par période"""
        if gb != 'of_gb_period_id':
            return super(ProjectTask, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'of_project_task_planning', 'id', 'task_id', 'period_id'),
            implicit=False, outer=True,
        )

        field_name = 'period_id'

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".%s' % (alias, field_name)
        }
