# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta


class OfAffectationTache(models.Model):
    _name = "of.affectation.tache"

    tache_id = fields.Many2one('project.task', string="tache")
    periode_id = fields.Many2one('of.periode.planifiee', string=u"Période")
    temps_affecte = fields.Float(string=u"Temps affecté")
    name = fields.Date(string="Nom", related="periode_id.premier_jour")
    temps_effectue = fields.Float(string=u"Temps effectué", compute="_compute_temps_effectue")
    user_id = fields.Many2one(comodel_name='res.users', string=u"Ressource")

    @api.depends('tache_id', 'tache_id.timesheet_ids')
    def _compute_temps_effectue(self):
        """ Permet de calculer le temps effectué sur la période
        """
        for time_periode in self:
            records = time_periode.tache_id.timesheet_ids.filtered(
                lambda ts: time_periode.periode_id.premier_jour <= ts.date <= time_periode.periode_id.dernier_jour)
            time_periode.temps_effectue = sum(records.mapped('unit_amount'))
        return


class OfPeriodePlanifiee(models.Model):
    _name = "of.periode.planifiee"
    _inherit = ["of.readgroup"]
    _order = 'premier_jour'

    @api.model
    def _search_gb_user_id(self, operator, value):
        return [('technicien_ids.user_id', operator, value)]

    @api.model
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
    dernier_jour = fields.Date(string="Dernier jour", compute="_compute_dernier_jour", store=True)
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

    gb_user_id = fields.Many2one(
        'res.users', compute=lambda s: None, search='_search_gb_user_id', string="Utilisateur",
        of_custom_groupby=True)
    gb_category_id = fields.Many2one(
        'project.category', compute=lambda s: None, search='_search_gb_category_id', string=u"Catégorie",
        of_custom_groupby=True)

    planification_alert = fields.Boolean(string=u"Alerte de planification", compute='_compute_planification')
    planification_ok = fields.Boolean(string=u"Planification OK", compute='_compute_planification')
    planification_exceed = fields.Boolean(string=u"Trop de planification", compute='_compute_planification')

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
    def _compute_dernier_jour(self):
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
                    periode.name = "S%02d - %s" % (week_nb, date.strftime('%b %Y'))
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
            period.planification_alert = period.technicien_ids.filtered(lambda tech: tech.occupation_rate < 50.0)
            period.planification_ok = not period.technicien_ids.filtered(
                lambda tech: tech.occupation_rate < 90.0 or tech.occupation_rate > 100.0)
            period.planification_exceed = period.technicien_ids.filtered(lambda tech: tech.occupation_rate > 100.0)

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

    periode_id = fields.Many2one(comodel_name='of.periode.planifiee', string=u"Période")
    user_id = fields.Many2one(comodel_name='res.users', string=u"Ressource", required=True)
    type = fields.Selection(
        selection=[('tech', u"Technique"), ('cust', u"Client")], string=u"Type")
    temps_de_travail = fields.Float(string="Temps de travail", required=True)
    temps_restant_task = fields.Float(string=u'Temps restant à affecter (tâches)', compute='_compute_temps_restant')
    temps_restant_categ = fields.Float(
        string=u"Temps restant à affecter (catégories)", compute='_compute_temps_restant')
    temps_effectue = fields.Float(string=u"Temps réalisé", compute='_compute_temps_restant')
    assigned_duration = fields.Float(string=u"Temps affecté", compute='_compute_temps_restant')
    occupation_rate = fields.Float(string=u"Taux d'occupation (%)", compute='_compute_temps_restant')
    category_ids = fields.One2many('of.periode.planifiee.category', 'technicien_id', copy=True)
    name = fields.Char(string='Nom', related='user_id.name', readonly=True)
    task_planning_ids = fields.Many2many(
        comodel_name='of.project.task.planning', compute='_compute_task_planning_ids',
        inverse='_inverse_task_planning_ids', string=u"Planification des tâches")

    @api.depends('temps_de_travail', 'category_ids', 'category_ids.temps_prevu')
    def _compute_temps_restant(self):
        """ Calcul du temps restant en récupérant les informations
        des catégories
        """
        activity_obj = self.env['account.analytic.line']
        for tech in self:
            tech.temps_restant_categ = tech.temps_de_travail - sum(tech.category_ids.mapped('temps_prevu'))
            task_plannings = self.env['of.project.task.planning'].search(
                [('period_id', '=', tech.periode_id.id), ('user_id', '=', tech.user_id.id)])
            tech.assigned_duration = sum(task_plannings.mapped('duration'))
            tech.temps_restant_task = tech.temps_de_travail - tech.assigned_duration
            if tech.temps_de_travail:
                tech.occupation_rate = (tech.assigned_duration / tech.temps_de_travail) * 100.0
            else:
                # Special case for "To affect" ressource
                tech.occupation_rate = 100.0
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

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'temps_de_travail' not in fields:
            fields.append('temps_de_travail')
        if 'assigned_duration' not in fields:
            fields.append('assigned_duration')
        res = super(OfPeriodePlanifieeTechnicien, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            line_domain = '__domain' in line and line['__domain'] or domain
            if 'temps_restant_categ' in fields:
                records = self.env['of.periode.planifiee.technicien'].search(line_domain)
                line['temps_restant_categ'] = \
                    line.get('temps_de_travail', 0.0) - sum(records.mapped('category_ids.temps_prevu'))
            if 'assigned_duration' in fields:
                records = self.env['of.periode.planifiee.technicien'].search(line_domain)
                task_plannings = self.env['of.project.task.planning'].search(
                    [('period_id', 'in', records.mapped('periode_id.id')),
                     ('user_id', 'in', records.mapped('user_id.id'))])
                line['assigned_duration'] = sum(task_plannings.mapped('duration'))
            if 'temps_restant_task' in fields:
                if 'temps_de_travail' in line and line['temps_de_travail'] is not None and \
                        'assigned_duration' in line and line['assigned_duration'] is not None:
                    line['temps_restant_task'] = line['temps_de_travail'] - line['assigned_duration']
            if 'occupation_rate' in fields:
                if 'assigned_duration' in line and line['assigned_duration'] is not None and \
                        line.get('temps_de_travail', False):
                    line['occupation_rate'] = (line['assigned_duration'] / line['temps_de_travail']) * 100.0
                else:
                    line['occupation_rate'] = False
            if 'temps_effectue' in fields:
                records = self.env['of.periode.planifiee.technicien'].search(line_domain)
                activities = self.env['account.analytic.line']
                for record in records:
                    activities |= self.env['account.analytic.line'].search(
                        [('date', '>=', record.periode_id.premier_jour),
                         ('date', '<=', record.periode_id.dernier_jour),
                         ('user_id', '=', record.user_id.id)])
                line['temps_effectue'] = sum(activities.mapped('unit_amount'))

        return res


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
