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
    period_id = fields.Many2one(comodel_name='of.periode.planifiee', string=u"Période")
    duration = fields.Float(string=u"Durée")
    notes = fields.Char(string=u"Notes")

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
