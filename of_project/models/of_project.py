# -*- coding: utf-8 -*-

import json

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta


class OfPeriodePlanifiee(models.Model):
    _name = "of.periode.planifiee"
    _inherit = ["of.readgroup"]
    _order = 'premier_jour'

    def _search_gb_user_id(self, operator, value):
        return [('technicien_ids.user_id', operator, value)]

    def _search_gb_category_id(self, operator, value):
        return [('technicien_ids.category_ids.categorie_id', operator, value)]

    @api.model
    def _search_name(self, operator, value):
        """ Permet de rechercher sur le nom (champ calculé donc pas en db)
        """
        periodes = self.search([]).filtered(lambda p: value in p.name)
        op = 'in' if (operator in ['=', 'like', 'ilike']) else 'not in'
        return [('id', op, periodes.ids)]

    type = fields.Selection([('mois', 'Mois'), ('semaine', 'Semaine')], string=u"Type de période", required=True)
    premier_jour = fields.Date(string="Premier jour", required=True)
    dernier_jour = fields.Date(string="Dernier jour", compute="_compute_duree", store=True)
    name = fields.Char(string="Nom", compute="_compute_name", search="_search_name")
    active = fields.Boolean(string="Actif", default=True)
    technicien_ids = fields.One2many('of.periode.planifiee.technicien', 'periode_id', copy=True)
    tech_total_time = fields.Float(string=u"Temp total technique", compute='_compute_time')
    tech_planned_time = fields.Float(string=u"Temps planifié technique", compute='_compute_time')
    tech_planned_time_perc = fields.Float(string=u"Temps planifié technique (%)", compute='_compute_time')
    tech_remaining_task_time = fields.Float(string=u"Reste à planifier technique (tâches)", compute='_compute_time')
    tech_remaining_categ_time = fields.Float(
        string=u"Reste à planifier technique (catégories)", compute='_compute_time')
    tech_done_time = fields.Float(string=u"Temps produit technique", compute='_compute_time')
    tech_done_time_perc = fields.Float(string=u"Temps produit technique (%)", compute='_compute_time')
    cust_total_time = fields.Float(string=u"Temp total client", compute='_compute_time')
    cust_planned_time = fields.Float(string=u"Temps planifié client", compute='_compute_time')
    cust_planned_time_perc = fields.Float(string=u"Temps planifié client (%)", compute='_compute_time')
    cust_remaining_task_time = fields.Float(string=u"Reste à planifier client (tâches)", compute='_compute_time')
    cust_remaining_categ_time = fields.Float(
        string=u"Reste à planifier client (catégories)", compute='_compute_time')
    cust_done_time = fields.Float(string=u"Temps produit client", compute='_compute_time')
    cust_done_time_perc = fields.Float(string=u"Temps produit client (%)", compute='_compute_time')


    gb_user_id = fields.Many2one('res.users', compute='lambda *a, **k:{}', search='_search_gb_user_id',
                                 string="Utilisateur", of_custom_groupby=True)
    gb_category_id = fields.Many2one('project.category', compute='lambda *a, **k:{}', search='_search_gb_category_id',
                                     string=u"Catégorie", of_custom_groupby=True)

    planification_alert = fields.Boolean(string=u"Alerte de planification", compute='_compute_planification')
    planification_ok = fields.Boolean(string=u"Planification OK", compute='_compute_planification')

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """ Ajout de la possibilité de regrouper par utilisateur
        ou par catégori de tâche
        """
        if gb not in ('gb_user_id', 'gb_category_id'):
            return super(OfPeriodePlanifiee, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'of_periode_planifiee_technicien', 'id', 'periode_id', 'user_id'),
            implicit=False, outer=True,
        )

        field_name = 'user_id'

        if gb == 'gb_category_id':

            alias, _ = query.add_join(
                (alias, 'of_periode_planifiee_category', 'id', 'technicien_id', 'categorie_id')
                )

            field_name = 'categorie_id'

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".%s' % (alias, field_name)
        }

    @api.onchange('type')
    def onchange_type(self):
        """ Recalcul du premier et dernier jour en fonction du type
        """
        if self.premier_jour:
            date = datetime.strptime(self.premier_jour, "%Y-%m-%d")
        else:
            date = datetime.today()
        if self.type == 'mois':
            date -= relativedelta(days=(date.day - 1))
            self.premier_jour = date.strftime('%Y-%m-%d')
            self.dernier_jour = (date + relativedelta(months=1, days=-1)).strftime('%Y-%m-%d')
        elif self.type == 'semaine':
            date -= relativedelta(days=date.weekday())
            self.premier_jour = date.strftime('%Y-%m-%d')
            self.dernier_jour = (date + relativedelta(days=6)).strftime('%Y-%m-%d')

    @api.depends('premier_jour', 'type')
    def _compute_duree(self):
        """ Calcul du dernier jour en fonction du premier jour
        et change le premier jour pour correspondre au premier
        jour du mois ou de la semaine en fonction de la semaine
        """
        for periode in self:
            if periode.premier_jour:
                date = datetime.strptime(periode.premier_jour, "%Y-%m-%d")
                if periode.type == 'mois':
                    date -= relativedelta(days=(date.day - 1))
                    periode.premier_jour = date.strftime('%Y-%m-%d')
                    periode.dernier_jour = (date + relativedelta(months=1, days=-1)).strftime('%Y-%m-%d')
                elif periode.type == 'semaine':
                    date -= relativedelta(days=date.weekday())
                    periode.premier_jour = date.strftime('%Y-%m-%d')
                    periode.dernier_jour = (date + relativedelta(days=6)).strftime('%Y-%m-%d')

    @api.depends('premier_jour')
    def _compute_name(self):
        """ Calcul le nom en fonction du premier jour et du type
        """
        for periode in self:
            if periode.premier_jour:
                date = datetime.strptime(periode.premier_jour, "%Y-%m-%d")
                if periode.type == 'semaine':
                    week_nb = date.isocalendar()[1]
                    periode.name = "S%02d - %s" % (week_nb, date.strftime('%Y'))
                if periode.type == 'mois':
                    periode.name = date.strftime('%B - %Y')

    @api.depends('technicien_ids')
    def _compute_time(self):
        """
        Permet de calculer les différentes informations relative au temps renseigné sur les ressources
        """
        for periode in self:
            # Technique
            periode.tech_total_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'tech').mapped('temps_de_travail'))
            periode.tech_remaining_task_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'tech').mapped('temps_restant_task'))
            periode.tech_remaining_categ_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'tech').mapped('temps_restant_categ'))
            periode.tech_planned_time = periode.tech_total_time - periode.tech_remaining_task_time
            periode.tech_done_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'tech').mapped('temps_effectue'))
            if periode.tech_total_time:
                periode.tech_planned_time_perc = periode.tech_planned_time / periode.tech_total_time * 100.0
                periode.tech_done_time_perc = periode.tech_done_time / periode.tech_total_time * 100.0
            else:
                periode.tech_planned_time_perc = 0.0
                periode.tech_done_time_perc = 0.0
            # Client
            periode.cust_total_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'cust').mapped('temps_de_travail'))
            periode.cust_remaining_task_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'cust').mapped('temps_restant_task'))
            periode.cust_remaining_categ_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'cust').mapped('temps_restant_categ'))
            periode.cust_planned_time = periode.cust_total_time - periode.cust_remaining_task_time
            periode.cust_done_time = sum(
                periode.technicien_ids.filtered(lambda t: t.type == 'cust').mapped('temps_effectue'))
            if periode.cust_total_time:
                periode.cust_planned_time_perc = periode.cust_planned_time / periode.cust_total_time * 100.0
                periode.cust_done_time_perc = periode.cust_done_time / periode.cust_total_time * 100.0
            else:
                periode.cust_planned_time_perc = 0.0
                periode.cust_done_time_perc = 0.0

    @api.depends('technicien_ids', 'technicien_ids.temps_restant_task')
    def _compute_planification(self):
        """
        Permet de calculer le niveau de planification (alerte ou OK)
        """
        for period in self:
            period.planification_alert = period.technicien_ids.filtered(lambda tech: tech.temps_restant_task < 0.0)
            period.planification_ok = not period.technicien_ids.filtered(lambda tech: tech.temps_restant_task != 0.0)


    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ Permet de rechercher uniquement les périodes avec l'utilisateur
        de la tâche et ayant du temps restant pour la catégorie de la tâche
        """
        res = super(OfPeriodePlanifiee, self).name_search(name=name, args=args, operator=operator, limit=limit)
        if self._context.get('from_task', False):
            user_id = self._context.get('user_id', False)
            categ_id = self._context.get('categ_id', False)
            objects = self.browse([x[0] for x in res])
            tech = objects.mapped('technicien_ids').filtered(lambda t: t.user_id.id == user_id)
            res = tech.mapped('category_ids').filtered(
                lambda c: c.categorie_id.id == categ_id and c.temps_restant > 0).mapped('periode_id')
            res = [(plan.id, plan.name) for plan in res]
        return res


class OfPeriodePlanifieeTechnicien(models.Model):
    _name = "of.periode.planifiee.technicien"

    periode_id = fields.Many2one('of.periode.planifiee')
    user_id = fields.Many2one('res.users', string=u"Ressource", required=True)
    type = fields.Selection(
        selection=[('tech', u"Technique"), ('cust', u"Client")], string=u"Type")
    temps_de_travail = fields.Float(string="Temps de travail", required=True)
    temps_restant_task = fields.Float(string=u'Temps restant à affecter (tâches)', compute="_get_temps_restant")
    temps_restant_categ = fields.Float(string=u"Temps restant à affecter (catégories)", compute="_get_temps_restant")
    temps_effectue = fields.Float(string=u"Temps effectué", compute="_get_temps_restant")
    category_ids = fields.One2many('of.periode.planifiee.category', 'technicien_id', copy=True)
    name = fields.Char(string='Nom', related='user_id.name', readonly=True)
    task_planning_ids = fields.Many2many(
        comodel_name='of.project.task.planning', compute='_compute_task_planning_ids',
        inverse='_inverse_task_planning_ids', string=u"Planification des tâches")

    @api.model
    def create(self, vals):
        res = super(OfPeriodePlanifieeTechnicien, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        """ Hack : lors de la création d'un One2many dans un One2many
        write est appelé en retirant le lien avec l'objet d'origine
        """
        if 'periode_id' in vals and not vals.get('periode_id', False):
            del vals['periode_id']
        res = super(OfPeriodePlanifieeTechnicien, self).write(vals)
        return res

    @api.depends('temps_de_travail', 'category_ids', 'category_ids.temps_prevu')
    def _get_temps_restant(self):
        """ Calcul du temps restant en récupérant les informations
        des catégories
        """
        activity_obj = self.env['account.analytic.line']
        for tech in self:
            if tech.temps_de_travail:
                tech.temps_restant_categ = tech.temps_de_travail - sum(tech.category_ids.mapped('temps_prevu'))
                task_plannings = self.env['of.project.task.planning'].search(
                    [('period_id', '=', tech.periode_id.id), ('user_id', '=', tech.user_id.id)])
                tech.temps_restant_task = tech.temps_de_travail - sum(task_plannings.mapped('duration'))
            if not isinstance(tech.periode_id.id, models.NewId) and tech.user_id:
                activities = activity_obj.search(
                    [('date', '>=', tech.periode_id.premier_jour),
                     ('date', '<=', tech.periode_id.dernier_jour),
                     ('user_id', '=', tech.user_id.id)])
                tech.temps_effectue = sum(activities.mapped('unit_amount'))

    @api.depends('user_id', 'periode_id')
    def _compute_task_planning_ids(self):
        for period_ressource in self:
            period_ressource.task_planning_ids = self.env['of.project.task.planning'].search(
                [('user_id', '=', period_ressource.user_id.id), ('period_id', '=', period_ressource.periode_id.id)])

    def _inverse_task_planning_ids(self):
        for period_ressource in self:
            if not period_ressource.task_planning_ids:
                task_plannings = self.env['of.project.task.planning'].search(
                    [('user_id', '=', period_ressource.user_id.id), ('period_id', '=', period_ressource.periode_id.id)])
                if task_plannings:
                    tasks = task_plannings.mapped('task_id')
                    task_plannings.unlink()
                    for task in tasks:
                        task.onchange_of_planning_ids()
            for task_planning in period_ressource.task_planning_ids:
                if isinstance(task_planning.id, models.NewId):
                    new_task_planning = self.env['of.project.task.planning'].create(
                        {'period_id': self.periode_id.id,
                         'user_id': self.user_id.id,
                         'task_id': task_planning.task_id.id,
                         'type_id': task_planning.type_id.id,
                         'duration': task_planning.duration,
                         'notes': task_planning.notes})
                    new_task_planning.task_id.onchange_of_planning_ids()
                elif not isinstance(task_planning.id, basestring):
                    task_planning.task_id.onchange_of_planning_ids()


class OfPeriodePlanifieeCategory(models.Model):
    _name = "of.periode.planifiee.category"

    technicien_id = fields.Many2one('of.periode.planifiee.technicien', string="Ressource")
    categorie_id = fields.Many2one('project.category', string=u"Catégorie", required=True)
    periode_id = fields.Many2one(
        'of.periode.planifiee', string=u"Période", related="technicien_id.periode_id", readonly=True)
    temps_prevu = fields.Float(string=u'Temps prévu')
    temps_restant = fields.Float(string="Temps restant", compute="_compute_temps_restant")
    name = fields.Char(string="Nom", related="categorie_id.name", readonly=True)

    @api.depends('technicien_id', 'temps_prevu')
    def _compute_temps_restant(self):
        """
        Calcul le temps restant à affecter en fonction des tâches et de la période
        """
        for period_categ in self:
            rest = 0
            if not isinstance(period_categ.periode_id.id, models.NewId):
                if period_categ.technicien_id and period_categ.categorie_id and period_categ.periode_id:
                    task_planning_ids = self.env['of.project.task.planning'].search(
                        [('period_id', '=', period_categ.periode_id.id),
                         ('user_id', '=', period_categ.technicien_id.user_id.id),
                         ('task_id.categ_id', '=', period_categ.categorie_id.id)])
                    rest = sum(task_planning_ids.mapped('duration'))
            period_categ.temps_restant = period_categ.temps_prevu - rest
        return


class OfAffectationTache(models.Model):
    _name = "of.affectation.tache"

    tache_id = fields.Many2one('project.task', string="tache")
    periode_id = fields.Many2one('of.periode.planifiee', string=u"Période")
    temps_affecte = fields.Float(string=u"Temps affecté")
    name = fields.Date(string="Nom", related="periode_id.premier_jour")
    temps_effectue = fields.Float(string=u"Temps effectué", compute="_compute_temps")
    user_id = fields.Many2one(comodel_name='res.users', string=u"Ressource")

    @api.depends('tache_id', 'tache_id.timesheet_ids')
    def _compute_temps(self):
        """ Permet de calculer le temps effectué sur la période
        """
        for time_periode in self:
            records = time_periode.tache_id.timesheet_ids.filtered(
                lambda ts: time_periode.periode_id.premier_jour <= ts.date <= time_periode.periode_id.dernier_jour)
            time_periode.temps_effectue = sum(records.mapped('unit_amount'))
        return


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
    of_total_planned_hours = fields.Float(string=u"Durée prévue", compute='_compute_time')
    of_total_done_hours = fields.Float(string=u"Durée réalisée", compute='_compute_time')
    of_ressources = fields.Text(string=u"Ressources", compute='_compute_of_ressources')
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

    planned_hours = fields.Float(compute='_compute_planned_hours', store=True)
    of_planned_dev_hours = fields.Float(string=u"Heures de développement")
    of_planned_review_hours = fields.Float(string=u"Heures de revue")
    project_id = fields.Many2one(required=True)
    categ_id = fields.Many2one(string=u"Catégorie", required=True)
    of_ticket_ids = fields.One2many(
        comodel_name='website.support.ticket', string=u"Tickets supports", compute='_compute_of_tickets')
    of_ticket_count = fields.Integer(string=u"Nombre de tickets", compute='_compute_of_tickets')
    of_review_description = fields.Html(string=u"Revue")
    of_gb_period_id = fields.Many2one(
        comodel_name='of.periode.planifiee', compute='lambda *a, **k:{}', search='_search_of_gb_period_id',
        string=u"Période", of_custom_groupby=True)
    of_user_id = fields.Many2one(comodel_name='res.users', string='Relecteur')
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

    @api.multi
    def _compute_of_tickets(self):
        for task in self:
            task.of_ticket_ids = self.env['website.support.ticket'].search([('of_task_id', '=', task.id)])
            task.of_ticket_count = len(task.of_ticket_ids)

    @api.onchange('of_planning_ids', 'of_planning_ids.period_id')
    def onchange_of_planning_ids(self):
        """
        Recalcul les dates de début et fin de tâches en fonction de la planification
        """
        if self.of_planning_ids:
            self.date_start = min(self.of_planning_ids.mapped('period_id').mapped('premier_jour'))
            self.date_end = max(self.of_planning_ids.mapped('period_id').mapped('dernier_jour'))

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

    @api.multi
    def action_view_tickets(self):
        action = self.env.ref('website_support.website_support_ticket_action_partner').read()[0]
        if len(self._ids) == 1:
            context = {
                'default_of_task_id': self.id,
            }
            action['context'] = str(context)
        action['domain'] = [('of_task_id', 'in', self._ids)]
        action['view_mode'] = 'tree,form'
        action['views'] = [(False, u'tree'), (False, u'form')]
        return action


class OFProjectTaskPlanning(models.Model):
    _name = 'of.project.task.planning'

    state = fields.Selection(
        selection=[('to_validate', u"À valider"), ('validated', u"Validé")], string=u"État", default='validated')
    task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche", required=True, ondelete='cascade')
    project_id = fields.Many2one(
        comodel_name='project.project', related='task_id.project_id', string=u"Projet", readonly=True)
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


class WebsiteSupportTicket(models.Model):
    _inherit = 'website.support.ticket'

    of_task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche associée")

    @api.multi
    def name_get(self):
        result = []
        for ticket in self:
            result.append((ticket.id, "%s - %s" % (ticket.ticket_number, ticket.subject)))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('subject', operator, name), ('ticket_number', operator, name)]
        tickets = self.search(domain + args, limit=limit)
        return tickets.name_get()
