# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class OfProjectStage(models.Model):
    _name = 'of.project.stage'
    _description = u"Étape de projet"
    _order = 'sequence, id'

    name = fields.Char(string=u"Nom de l'étape", required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=1)
    fold = fields.Boolean(string=u"Replié dans la vue Kanban")


class Project(models.Model):
    _inherit = 'project.project'
    _order = 'of_task_total_priority desc, of_end_date'

    def _default_stage_id(self):
        return self.env['of.project.stage'].search([('fold', '=', False)], limit=1).id

    of_state = fields.Selection(
        selection=[('01_incoming', u"À venir"),
                   ('02_in_progress', u"En cours"),
                   ('03_on_hold', u"En attente"),
                   ('04_closed', u"Fermé")], compute='_compute_of_state', string=u"État", store=True)
    of_stage_id = fields.Many2one(
        'of.project.stage', string=u"Étape", default=lambda self: self._default_stage_id(),
        group_expand='_read_group_stage_ids')
    of_start_date = fields.Date(compute='_compute_of_dates', string=u"Date de début", store=True)
    of_end_date = fields.Date(compute='_compute_of_dates', string=u"Date de fin", store=True)
    of_sale_id = fields.Many2one(
        'sale.order', string=u"Commande client", domain="[('partner_id', 'child_of', partner_id)]")
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

    @api.onchange('of_sale_id')
    def _onchange_of_sale_id(self):
        if self.of_sale_id and not self.partner_id:
            self.partner_id = self.of_sale_id.partner_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.of_sale_id = False

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order=order)

    @api.multi
    def get_partner_action(self):
        self.ensure_one()
        # Le module contacts est une dépendance indirecte de ce module
        action = self.env.ref('contacts.action_contacts').read()[0]
        action['res_id'] = self.partner_id.id
        action['view_mode'] = "form"
        action['views'] = False
        return action

    @api.multi
    def get_sale_order_action(self):
        self.ensure_one()
        action = self.env.ref('sale.action_orders').read()[0]
        action['res_id'] = self.of_sale_id.id
        action['view_mode'] = "form"
        action['views'] = False
        return action


class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'of.readgroup']

    user_id = fields.Many2one(domain="[('share', '=', False)]")
    project_id = fields.Many2one(required=True)
    categ_id = fields.Many2one(string=u"Catégorie", required=True)
    of_members = fields.Many2many('res.users', string=u"Membres", related='project_id.members')
    of_participant_ids = fields.Many2many('res.users', string=u"Participants")

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

    @api.onchange('user_id')
    def _onchange_user(self):
        # Désactivation du _onchange_user qui remet le champ date_start à la date actuelle.
        pass
