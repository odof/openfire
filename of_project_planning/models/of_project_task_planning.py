# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFProjectTaskPlanning(models.Model):
    _name = 'of.project.task.planning'
    _order = 'period_id, type_id'

    name = fields.Char(string=u"Nom", compute='_compute_name', store=True)
    state = fields.Selection(
        selection=[
            ('draft', u"Brouillon"),
            ('to_validate', u"À faire"),
            ('waiting', u"En attente"),
            ('validated', u"Terminée"),
            ('cancel', u"Annulée"),
        ], string=u"État", default='draft')
    task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche", required=True, ondelete='cascade')
    project_id = fields.Many2one(
        comodel_name='project.project', related='task_id.project_id', string=u"Projet", readonly=True, store=True)
    task_stage_id = fields.Many2one(
        comodel_name='project.task.type', related='task_id.stage_id', string=u"Étape de la tâche", readonly=True)
    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='of_planned_activity_id', string=u"Feuilles de temps")
    progress = fields.Float(compute='_compute_progress', store=True, string=u"Temps enregistré", group_operator="avg")
    type_id = fields.Many2one(comodel_name='of.project.task.planning.type', string=u"Type", required=True)
    timesheet_type = fields.Selection(related='type_id.timesheet_type', readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u"Ressource")
    period_id = fields.Many2one(
        comodel_name='of.periode.planifiee', string=u"Période", group_expand='_read_group_period_ids')
    period_start_date = fields.Date(
        related='period_id.premier_jour', string=u"Date de début de période", store=True, readonly=True)
    period_end_date = fields.Date(
        related='period_id.dernier_jour', string=u"Date de fin de période", store=True, readonly=True)
    duration = fields.Float(string=u"Durée")
    notes = fields.Char(string=u"Notes")
    color = fields.Char(related='type_id.color', string=u"Couleur", store=True, readonly=True)
    done_duration = fields.Float(string=u"Temps réalisé", compute='_compute_durations')
    occupation_rate = fields.Float(string=u"Taux d'occupation (%)", compute='_compute_durations')

    @api.depends('type_id', 'user_id', 'period_id')
    def _compute_name(self):
        for task_planning in self:
            name = task_planning.period_id and task_planning.period_id.name or u""
            name = task_planning.type_id and (name + u", " + task_planning.type_id.name) or name
            name = task_planning.user_id and (name + u", " + task_planning.user_id.name) or name
            task_planning.name = name

    @api.depends('analytic_line_ids.unit_amount', 'duration')
    def _compute_progress(self):
        for task_planning in self:
            effective_hours = sum(task_planning.analytic_line_ids.mapped('unit_amount'))

            if task_planning.duration > 0.0:
                task_planning.progress = round(100.0 * effective_hours / task_planning.duration, 2)
            else:
                task_planning.progress = 0.0

    @api.depends('period_id', 'user_id', 'task_id', 'duration')
    def _compute_durations(self):
        timesheet_obj = self.env['account.analytic.line']
        planned_period_line_obj = self.env['of.periode.planifiee.technicien']
        for task_planning in self:
            timesheets = timesheet_obj.search(
                [('date', '>=', task_planning.period_id.premier_jour),
                 ('date', '<=', task_planning.period_id.dernier_jour),
                 ('user_id', '=', task_planning.user_id.id),
                 ('task_id', '=', task_planning.task_id.id)])
            task_planning.done_duration = sum(timesheets.mapped('unit_amount'))

            planned_period_lines = planned_period_line_obj.search(
                [('user_id', '=', task_planning.user_id.id), ('periode_id', '=', task_planning.period_id.id)])
            work_duration = sum(planned_period_lines.mapped('temps_de_travail'))
            if work_duration:
                task_planning.occupation_rate = (task_planning.duration / work_duration) * 100.0
            else:
                task_planning.occupation_rate = 0

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'duration' not in fields:
            fields.append('duration')
        res = super(OFProjectTaskPlanning, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            line_domain = '__domain' in line and line['__domain'] or domain
            if 'done_duration' in fields:
                records = self.env['of.project.task.planning'].search(line_domain)
                timesheets = self.env['account.analytic.line']
                for record in records:
                    timesheets |= self.env['account.analytic.line'].search(
                        [('date', '>=', record.period_id.premier_jour),
                         ('date', '<=', record.period_id.dernier_jour),
                         ('user_id', '=', record.user_id.id),
                         ('task_id', '=', record.task_id.id)])
                line['done_duration'] = sum(timesheets.mapped('unit_amount'))
            if 'occupation_rate' in fields:
                if 'duration' in line and line['duration'] is not None:
                    records = self.env['of.project.task.planning'].search(line_domain)
                    planned_period_lines = self.env['of.periode.planifiee.technicien']
                    for record in records:
                        planned_period_lines |= self.env['of.periode.planifiee.technicien'].search(
                            [('user_id', '=', record.user_id.id),
                             ('periode_id', '=', record.period_id.id)])
                    work_duration = sum(planned_period_lines.mapped('temps_de_travail'))
                    if work_duration:
                        line['occupation_rate'] = (line['duration'] / work_duration) * 100.0
                    else:
                        line['occupation_rate'] = False
                else:
                    line['occupation_rate'] = False
        return res

    @api.model
    def _read_group_period_ids(self, stages, domain, order):
        if stages:
            first_stage = stages.sorted('premier_jour')[0]
            return self.env['of.periode.planifiee'].with_context(active_test=False).search(
                [('premier_jour', '>=', first_stage.premier_jour)])
        else:
            return self.env['of.periode.planifiee'].with_context(active_test=False).search([])


class OFProjectTaskPlanningType(models.Model):
    _name = 'of.project.task.planning.type'
    _order = 'sequence, name'

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom", required=True)
    active = fields.Boolean(string=u"Actif", default=True)
    timesheet_type = fields.Selection(
        selection=[
            ('spec', u"Spécifications"),
            ('dev', u"Développement"),
            ('validation', u"Validation"),
            ('other', u"Autre"),
        ], string=u"Type des feuilles de temps")
    color = fields.Char(string=u"Couleur", default="#FFFFFF")
