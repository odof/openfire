# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFProjectTaskPlanning(models.Model):
    _name = 'of.project.task.planning'
    _order = 'period_id, type_id'

    state = fields.Selection(
        selection=[('to_validate', u"À valider"), ('validated', u"Validé")], string=u"État", default='validated')
    task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche", required=True, ondelete='cascade')
    project_id = fields.Many2one(
        comodel_name='project.project', related='task_id.project_id', string=u"Projet", readonly=True, store=True)
    task_stage_id = fields.Many2one(
        comodel_name='project.task.type', related='task_id.stage_id', string=u"Étape de la tâche", readonly=True)
    type_id = fields.Many2one(comodel_name='of.project.task.planning.type', string=u"Type", required=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u"Ressource")
    period_id = fields.Many2one(comodel_name='of.periode.planifiee', string=u"Période")
    duration = fields.Float(string=u"Durée")
    notes = fields.Char(string=u"Notes")

    @api.multi
    def name_get(self):
        res = []
        for task_planning in self:
            res.append(
                (task_planning.id, '%s / %s' % (task_planning.task_id.name_get()[0][1], task_planning.type_id.name)))
        return res


class OFProjectTaskPlanningType(models.Model):
    _name = 'of.project.task.planning.type'
    _order = 'sequence, name'

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom", required=True)
    active = fields.Boolean(string=u"Actif", default=True)
