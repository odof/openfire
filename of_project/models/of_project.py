# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class Project(models.Model):
    _inherit = 'project.project'
    _order = 'of_task_total_priority desc, of_end_date'

    of_state = fields.Selection(
        selection=[('01_incoming', u"À venir"),
                   ('02_in_progress', u"En cours"),
                   ('03_on_hold', u"En attente"),
                   ('04_closed', u"Fermé")], compute='_compute_of_state', string=u"État", store=True)
    of_start_date = fields.Date(compute='_compute_of_dates', string=u"Date de début", store=True)
    of_end_date = fields.Date(compute='_compute_of_dates', string=u"Date de fin", store=True)
    of_start_week = fields.Char(compute='_compute_of_dates', string=u"Semaine de début", store=True)
    of_tag_ids = fields.Many2many(comodel_name='project.tags', string=u"Étiquettes")
    of_task_total_priority = fields.Integer(
        string=u"Priorité totale des tâches", compute='_compute_of_task_total_priority', store=True)

    @api.depends('task_ids', 'task_ids.stage_id', 'task_ids.stage_id.state')
    def _compute_of_state(self):
        """
        Calcul de l'état d'un projet en fonction de l'avancement de ses tâches
        """
        for project in self:
            if project.task_ids.filtered(lambda t: t.stage_id.state == 'open'):
                project.of_state = '02_in_progress'
            elif project.task_ids.filtered(lambda t: t.stage_id.state == 'draft'):
                project.of_state = '01_incoming'
            elif project.task_ids.filtered(lambda t: t.stage_id.state == 'pending'):
                project.of_state = '03_on_hold'
            else:
                project.of_state = '04_closed'

    @api.depends('task_ids', 'task_ids.date_start', 'task_ids.date_end')
    def _compute_of_dates(self):
        """
        Calcul des dates d'un projet en fonction des dates de ses tâches
        """
        for project in self:
            if project.task_ids.filtered(lambda t: t.date_start).mapped('date_start'):
                project.of_start_date = min(project.task_ids.filtered(lambda t: t.date_start).mapped('date_start'))

                date = datetime.strptime(project.of_start_date, "%Y-%m-%d")
                week_nb = date.isocalendar()[1]
                project.of_start_week = "%s S%02d" % (date.strftime('%Y'), week_nb)

            if project.task_ids.filtered(lambda t: t.date_end).mapped('date_end'):
                project.of_end_date = max(project.task_ids.filtered(lambda t: t.date_end).mapped('date_end'))

    @api.depends('task_ids', 'task_ids.priority')
    def _compute_of_task_total_priority(self):
        """
        Calcul de la priorité d'un projet en fonction des priorités de ses tâches
        """
        for project in self:
            project.of_task_total_priority = sum(project.task_ids.mapped(lambda t: int(t.priority)))


class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'of.readgroup']

    project_id = fields.Many2one(required=True)
    categ_id = fields.Many2one(string=u"Catégorie", required=True)

    @api.multi
    def name_get(self):
        result = []
        for task in self:
            result.append((task.id, "%s - %s" % (task.code, task.name)))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        tasks = self.search(domain + args, limit=limit)
        return tasks.name_get()
