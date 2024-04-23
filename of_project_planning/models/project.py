# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import models, fields, api


class Project(models.Model):
    _inherit = 'project.project'

    of_total_planned_hours = fields.Float(string=u"Durée planifiée", compute='_compute_time')
    of_total_done_hours = fields.Float(string=u"Durée réalisée", compute='_compute_time')
    of_ressources = fields.Text(string=u"Ressources", compute='_compute_of_ressources')
    of_progress_rate = fields.Float(
        string=u"Taux d'avancement (%)", compute='_compute_of_progress_rate', store=True, digits=(16, 2))
    of_consumption_rate = fields.Float(
        string=u"Taux de consommation (%)", compute='_compute_of_consumption_rate', store=True, digits=(16, 2))

    @api.depends('tasks', 'tasks.of_planned_hours', 'tasks.effective_hours')
    def _compute_time(self):
        """
        Calcul les temps consolidés d'un projet en fonction des temps de ses tâches
        """
        for project in self:
            project.of_total_planned_hours = sum(project.tasks.mapped('of_planned_hours'))
            project.of_total_done_hours = sum(project.tasks.mapped('effective_hours'))

    @api.depends('task_ids', 'task_ids.of_planning_ids', 'task_ids.of_planning_ids.user_id')
    def _compute_of_ressources(self):
        for project in self:
            ressources = []
            all_ressources = set(
                project.task_ids.mapped('of_planning_ids').filtered(lambda p: p.user_id).mapped('user_id'))
            for user in all_ressources:
                ressources.append({'id': user.id, 'name': user.name})
            project.of_ressources = json.dumps(ressources) if ressources else False

    @api.depends('tasks', 'tasks.of_progress_rate', 'tasks.of_planned_hours')
    def _compute_of_progress_rate(self):
        for project in self:
            total_planned_duration = sum(project.mapped('tasks.of_planned_hours'))
            if total_planned_duration:
                total_progress = sum(
                    [(task.of_planned_hours * task.of_progress_rate / 100.0) for task in project.tasks])
                project.of_progress_rate = (total_progress / total_planned_duration) * 100.0
            else:
                project.of_progress_rate = 0

    @api.depends('tasks', 'tasks.of_done_hours', 'tasks.of_planned_hours')
    def _compute_of_consumption_rate(self):
        for project in self:
            total_planned_duration = sum(project.mapped('tasks.of_planned_hours'))
            if total_planned_duration:
                total_consumption = sum(project.mapped('tasks.of_done_hours'))
                project.of_consumption_rate = (total_consumption / total_planned_duration) * 100.0
            else:
                project.of_consumption_rate = 0


class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.model_cr_context
    def _auto_init(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_project_planning'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_self.latest_version
            if version < '10.0.2':
                # à cette version, des vues XML de modules enfants perdent leur accroche xpath,
                # on les désactive donc pour permettre la MÀJ
                cr = self.env.cr
                cr.execute("""
    -- forcer le recalcul of_user_ids,
    DROP TABLE project_task_res_users_rel;

    -- à cette version, les champs dont dépend planned_hours sont nouveaux et valent tous 0
    UPDATE project_task
    SET planned_hours = 0;
                """)
                cr.commit()
        return super(ProjectTask, self)._auto_init()

    of_planif_state = fields.Selection([
        ('draft', u"Brouillon"),
        ('waiting', u"En attente"),
        ('todo', u"À faire"),
        ('cancel', u"Annulée"),
        ('done', u"Terminée"),
    ], string=u"État de planification", compute='_compute_of_planif_state', store=True)
    # réécriture planned_hours
    # planned_hours = spec_hours + dev_hours + validation_hours
    # of_planned_hours = sum(of_planning_ids.mapped('duration'))
    planned_hours = fields.Float(
        string=u"Durée initiale", compute='_compute_planned_hours', store=True,
        help=u"Calculée à partir des durées chiffrée")
    of_planned_hours = fields.Float(
        string=u"Durée Planifiée", compute='_compute_of_planned_hours', store=True,
        help=u"Calculée à partir des activités planifiées")
    of_spec_hours = fields.Float(string=u"Planif specs")
    of_dev_hours = fields.Float(string=u"Planif dev")
    of_validation_hours = fields.Float(string=u"Planif validation")
    of_done_hours = fields.Float(string=u"Durée passée", compute='_compute_of_done')
    of_done_spec_hours = fields.Float(string=u"Specs passées", compute='_compute_of_done')
    of_done_dev_hours = fields.Float(string=u"Dev passé", compute='_compute_of_done')
    of_done_validation_hours = fields.Float(string=u"Validation passée", compute='_compute_of_done')
    of_gb_period_id = fields.Many2one(
        comodel_name='of.periode.planifiee', compute=lambda s: None, search='_search_of_gb_period_id',
        string=u"Période", of_custom_groupby=True)
    of_analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='task_id', string=u"Feuilles de temps")
    of_planning_ids = fields.One2many(
        comodel_name='of.project.task.planning', inverse_name='task_id', string=u"Activités planifiées")
    # rendre le champ compute
    of_user_ids = fields.Many2many(compute='_compute_of_user_ids', store=True)
    of_progress_rate = fields.Integer(string=u"Taux d'avancement (%)")
    of_consumption_rate = fields.Float(
        string=u"Taux de consommation (%)", compute='_compute_of_consumption_rate', store=True, digits=(16, 2))

    def _search_of_gb_period_id(self, operator, value):
        return [('of_planning_ids.period_id', operator, value)]

    @api.depends('of_planning_ids.state', 'stage_id.state')
    def _compute_of_planif_state(self):
        for task in self:
            planif_states = set(task.of_planning_ids.mapped('state'))
            # mode "manuel" prioritaire pour les états "annulée" et "terminée"
            if task.stage_id.state and task.stage_id.state == 'cancelled' \
                    or len(planif_states) == 1 and 'cancel' in planif_states:
                task.of_planif_state = 'cancel'
            elif task.stage_id.state and task.stage_id.state == 'done':
                task.of_planif_state = 'done'
            elif 'waiting' in planif_states:
                task.of_planif_state = 'waiting'
            elif 'to_validate' in planif_states:
                task.of_planif_state = 'todo'
            # rien du reste, mais pas draft
            elif 'draft' not in planif_states and 'validated' in planif_states:
                task.of_planif_state = 'done'
            else:
                task.of_planif_state = 'draft'

    @api.depends('of_spec_hours', 'of_dev_hours', 'of_validation_hours')
    def _compute_planned_hours(self):
        for task in self:
            task.planned_hours = task.of_spec_hours + task.of_dev_hours + task.of_validation_hours

    @api.depends('of_planning_ids.duration')
    def _compute_of_planned_hours(self):
        for task in self:
            task.of_planned_hours = sum(task.of_planning_ids.mapped('duration'))

    @api.depends('of_analytic_line_ids', 'of_planning_ids.timesheet_type')
    def _compute_of_done(self):
        for task in self:
            analytic_lines = task.of_analytic_line_ids
            spec_lines = analytic_lines.filtered(
                lambda l: l.of_planned_activity_id.timesheet_type == 'spec' or l.of_categ_id.timesheet_type == 'spec')
            dev_lines = analytic_lines.filtered(
                lambda l: l.of_planned_activity_id.timesheet_type == 'dev' or l.of_categ_id.timesheet_type == 'dev')
            validation_lines = analytic_lines.filtered(
                lambda l: l.of_planned_activity_id.timesheet_type == 'validation' or
                          l.of_categ_id.timesheet_type == 'validation')
            task.of_done_hours = sum(analytic_lines.mapped('unit_amount'))
            task.of_done_spec_hours = sum(spec_lines.mapped('unit_amount'))
            task.of_done_dev_hours = sum(dev_lines.mapped('unit_amount'))
            task.of_done_validation_hours = sum(validation_lines.mapped('unit_amount'))

    @api.depends('of_planning_ids.user_id')
    def _compute_of_user_ids(self):
        for task in self:
            task.of_user_ids = task.of_planning_ids.mapped('user_id')

    @api.depends('of_planned_hours', 'of_analytic_line_ids', 'of_analytic_line_ids.unit_amount')
    def _compute_of_consumption_rate(self):
        for task in self:
            if task.of_planned_hours:
                task.of_consumption_rate = (task.of_done_hours / task.of_planned_hours) * 100.0
            else:
                task.of_consumption_rate = 0

    @api.onchange('of_planning_ids', 'of_planning_ids.period_id')
    def onchange_of_planning_ids(self):
        """
        Recalcul les dates de début et fin de tâches en fonction de la planification
        """
        periods = self.of_planning_ids and self.of_planning_ids.mapped('period_id')
        if periods:
            self.date_start = min(periods.mapped('premier_jour'))
            self.date_end = max(periods.mapped('dernier_jour'))

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

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(ProjectTask, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'of_progress_rate' in fields:
                line_domain = '__domain' in line and line['__domain'] or domain
                records = self.env['project.task'].search(line_domain)
                if len(records) > 1:
                    total_planned_duration = sum(records.mapped('of_planned_hours'))
                    if total_planned_duration:
                        total_progress = sum([(rec.of_planned_hours * rec.of_progress_rate / 100.0) for rec in records])
                        line['of_progress_rate'] = (total_progress / total_planned_duration) * 100.0
                    else:
                        line['of_progress_rate'] = False
            if 'of_consumption_rate' in fields:
                line_domain = '__domain' in line and line['__domain'] or domain
                records = self.env['project.task'].search(line_domain)
                if len(records) > 1:
                    total_planned_duration = sum(records.mapped('of_planned_hours'))
                    if total_planned_duration:
                        total_consumption = sum(records.mapped('of_done_hours'))
                        line['of_consumption_rate'] = (total_consumption / total_planned_duration) * 100.0
                    else:
                        line['of_consumption_rate'] = False

        return res
