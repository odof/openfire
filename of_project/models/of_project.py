# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID
from odoo.tools.safe_eval import safe_eval


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
        'sale.order', string=u"Commande liée", domain="[('partner_id', 'child_of', partner_id)]")
    of_start_week = fields.Char(compute='_compute_of_dates', string=u"Semaine de début", store=True)
    of_tag_ids = fields.Many2many(comodel_name='project.tags', string=u"Étiquettes")
    of_task_total_priority = fields.Integer(
        string=u"Priorité totale des tâches", compute='_compute_of_task_total_priority', store=True)
    of_planned_hours = fields.Float(string=u"Durée initiale", compute='_compute_planned_hours')

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

    @api.depends('task_ids', 'task_ids.planned_hours')
    def _compute_planned_hours(self):
        for project in self:
            project.of_planned_hours = sum(project.task_ids.mapped('planned_hours'))

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

    @api.model_cr_context
    def _auto_init(self):
        module_of_project_planning = self.env['ir.module.module'].search(
            [('name', '=', 'of_project_planning'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_of_project_planning:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_of_project_planning.latest_version
            if version < '10.0.2':
                # à cette version, des vues XML de modules enfants perdent leur accroche xpath,
                # on les désactive donc pour permettre la MÀJ
                cr = self.env.cr
                id_tup = (
                    self.env.ref('of_project_planning.of_project_planning_of_project_project_task_kanban_view').id,
                    self.env.ref('of_project_planning.of_project_planning_project_task_kanban_view').id)
                cr.execute("""
        -- désactiver les vues problématiques
        UPDATE ir_ui_view
        SET active = 'f'
        WHERE id in %s;
                    """, (id_tup,))
                cr.commit()

        return super(ProjectTask, self)._auto_init()

    user_id = fields.Many2one(domain="[('share', '=', False)]")
    project_id = fields.Many2one(required=True)
    categ_id = fields.Many2one(string=u"Catégorie", required=True)
    of_member_ids = fields.Many2many('res.users', string=u"Membres", related='project_id.members', readonly=True)
    # Attributs explicités pour respect des normes OF, mais la table existait déjà en BDD, d'où les noms
    of_user_ids = fields.Many2many(
        comodel_name='res.users', relation='project_task_res_users_rel', column1='project_task_id',
        column2='res_users_id', string=u"Ressource(s)", oldname='of_participant_ids')
    of_dependencies = fields.Text(string=u"Dépendances", compute='_compute_of_dependencies')
    of_participants = fields.Text(string=u"Ressource(s)", compute='_compute_of_participants')
    of_intervention_count = fields.Integer(string=u"RDV", compute='_compute_of_intervention_ids')
    of_intervention_ids = fields.One2many(
        comodel_name='of.planning.intervention', inverse_name='task_id',
        string=u"RDV", compute='_compute_of_intervention_ids')

    @api.multi
    def action_open_wizard_plan_intervention(self):
        self.ensure_one()
        context = self._context.copy()
        if not self.partner_id:
            raise UserError(_("There is no customer associated to this task. Please set one to plan an intervention."))
        if not self.partner_id.geo_lat and not self.partner_id.geo_lng:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))
        form_view_id = self.env.ref('of_planning_tournee.view_rdv_intervention_complete_form_wizard').id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.tournee.rdv',
            'res_id': False,
            'views': [(form_view_id, 'form')],
            'target': 'new',
            'context': context
        }

    @api.multi
    def action_view_interventions(self):
        action = self.env.ref('of_project.of_project_open_interventions').read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context.update({
                'default_address_id': self.partner_id and self.partner_id.id or False,
                'default_task_id': self.id,
                'default_duree': self.planned_hours,
                'default_employee_ids': [(6, 0, self.user_id and self.user_id.employee_ids.ids)],
            })
            if self.of_intervention_ids:
                context['force_date_start'] = self.of_intervention_ids[-1].date_date
                context['search_default_task_id'] = self.id
            action['context'] = str(context)
        action = self.mapped('of_intervention_ids').get_action_views(self, action)
        return action

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # On modifie la fonction _read_group_stage_ids pour ajouter les étapes qui doivent être visibles mêmes si vides
        visible_stages = self.env['project.task.type'].search([('of_visible_if_empty', '=', True)])
        stages += visible_stages
        search_domain = [('id', 'in', stages.ids)]
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain

        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.depends('of_user_ids')
    def _compute_of_participants(self):
        for task in self:
            participants = []
            for user in task.of_user_ids:
                participants.append({'id': user.id, 'name': user.name})
            task.of_participants = json.dumps(participants) if participants else False

    @api.depends('dependency_task_ids')
    def _compute_of_dependencies(self):
        for task in self:
            dependencies = []
            for dependency in task.dependency_task_ids:
                dependencies.append({'id': dependency.id, 'name': dependency.code})
            task.of_dependencies = json.dumps(dependencies) if dependencies else False

    @api.depends()
    def _compute_of_intervention_ids(self):
        """ Calcule du nombre de RDVs d'interventions liées à la tâche """
        intervention_obj = self.env['of.planning.intervention']
        for task in self:
            task.of_intervention_ids = intervention_obj.search([('task_id', '=', task.id)])
            task.of_intervention_count = len(task.of_intervention_ids)

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

    @api.multi
    def open_task(self):
        task_id = self._context.get('task_id')

        if task_id:
            action = {
                'name': 'Tache',
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'view_mode': 'form',
                'target': 'current',
                'res_id': task_id,
                'context': self._context,
            }
            return action

    @api.model
    def create(self, vals):
        res = super(ProjectTask, self).create(vals)
        if 'of_user_ids' in vals or 'user_id' in vals:
            user_obj = self.env['res.users']
            user_ids = []
            if vals.get('of_user_ids') and vals['of_user_ids'][0][2]:
                user_ids += vals['of_user_ids'][0][2]
            if 'user_id' in vals and vals['user_id']:
                user_ids += [vals['user_id']]
            users = user_obj.browse(user_ids)
            if users:
                for task in res:
                    if any(user.id not in task.project_id.members.ids for user in users):
                        task.project_id.members = [(6, 0, task.project_id.members.ids + users.ids)]
        return res

    @api.multi
    def write(self, vals):
        if 'stage_id' in vals:
            stage = self.env['project.task.type'].browse(vals['stage_id'])
            if stage.state == 'done':
                vals.update({'date_end': datetime.now()})
        if 'of_user_ids' in vals or 'user_id' in vals:
            user_obj = self.env['res.users']
            user_ids = []
            if vals.get('of_user_ids') and vals['of_user_ids'][0][2]:
                user_ids += vals['of_user_ids'][0][2]
            if 'user_id' in vals and vals['user_id']:
                user_ids += [vals['user_id']]
            users = user_obj.browse(user_ids)
            if users:
                for task in self:
                    if any(user.id not in task.project_id.members.ids for user in users):
                        task.project_id.members = [(6, 0, task.project_id.members.ids + users.ids)]
        return super(ProjectTask, self).write(vals)


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    of_visible_if_empty = fields.Boolean(
        string=u"Visible même si vide", default=True,
        help=u"La colonne de cette étape n'est pas affichée si elle est vide")
