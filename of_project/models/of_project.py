# -*- coding: utf-8 -*-

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
    dernier_jour = fields.Date(string="Dernier jour", compute="_compute_duree")
    name = fields.Char(string="Nom", compute="_compute_name", search="_search_name")
    active = fields.Boolean(string="Actif", default=True)
    technicien_ids = fields.One2many('of.periode.planifiee.technicien', 'periode_id', copy=True)
    temps_total = fields.Float(string="Temps Total", compute="_compute_temps")
    temps_prevu = fields.Float(string=u"Temps prévu", compute="_compute_temps")
    temps_restant_task = fields.Float(string=u"Temps restant à affecter (tâches)", compute="_compute_temps")
    temps_restant_categ = fields.Float(string=u"Temps restant à affecter (catégories)", compute="_compute_temps")
    temps_effectue = fields.Float(string=u"Temps effectué", compute="_compute_temps")
    gb_user_id = fields.Many2one('res.users', compute='lambda *a, **k:{}', search='_search_gb_user_id',
                                 string="Utilisateur", of_custom_groupby=True)
    gb_category_id = fields.Many2one('project.category', compute='lambda *a, **k:{}', search='_search_gb_category_id',
                                     string=u"Catégorie", of_custom_groupby=True)

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
    def _compute_temps(self):
        """ Permet de calculer les différentes informations
        relative au temps renseigné sur les techniciens
        """
        for periode in self:
            periode.temps_total = sum(periode.technicien_ids.mapped('temps_de_travail'))
            periode.temps_prevu = sum(periode.technicien_ids.mapped('category_ids').mapped('temps_prevu'))
            periode.temps_restant_task = sum(periode.technicien_ids.mapped('category_ids').mapped('temps_restant'))
            periode.temps_restant_categ = sum(periode.technicien_ids.mapped('temps_restant_categ'))
            periode.temps_effectue = sum(periode.technicien_ids.mapped('temps_effectue'))

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
    user_id = fields.Many2one('res.users', string="Technicien", required=True)
    temps_de_travail = fields.Float(string="Temps de travail", required=True)
    temps_restant_task = fields.Float(string=u'Temps restant à affecter (tâches)', compute="_get_temps_restant")
    temps_restant_categ = fields.Float(string=u"Temps restant à affecter (catégories)", compute="_get_temps_restant")
    temps_effectue = fields.Float(string=u"Temps effectué", compute="_get_temps_restant")
    category_ids = fields.One2many('of.periode.planifiee.category', 'technicien_id', copy=True)
    name = fields.Char(string='Nom', related='user_id.name', readonly=True)

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
                tech.temps_restant_task = sum(tech.category_ids.mapped('temps_restant'))
            if not isinstance(tech.periode_id.id, models.NewId) and tech.user_id:
                activities = activity_obj.search(
                    [('date', '>=', tech.periode_id.premier_jour),
                     ('date', '<=', tech.periode_id.dernier_jour),
                     ('user_id', '=', tech.user_id.id)])
                tech.temps_effectue = sum(activities.mapped('unit_amount'))


class OfPeriodePlanifieeCategory(models.Model):
    _name = "of.periode.planifiee.category"

    technicien_id = fields.Many2one('of.periode.planifiee.technicien', string="Technicien")
    categorie_id = fields.Many2one('project.category', string=u"Catégorie", required=True)
    periode_id = fields.Many2one(
        'of.periode.planifiee', string=u"Période", related="technicien_id.periode_id", readonly=True)
    temps_prevu = fields.Float(string=u'Temps prévu')
    temps_restant = fields.Float(string="Temps restant", compute="_compute_temps_restant")
    name = fields.Char(string="Nom", related="categorie_id.name", readonly=True)

    @api.depends('technicien_id', 'temps_prevu')
    def _compute_temps_restant(self):
        """ Calcul le temps restant à affecter en fonction des tâches
        et de la période
        """
        task_obj = self.env['project.task']
        for period_categ in self:
            rest = 0
            if not isinstance(period_categ.periode_id.id, models.NewId):
                if period_categ.technicien_id and period_categ.categorie_id and period_categ.periode_id:
                    tasks = task_obj.search([('categ_id', '=', period_categ.categorie_id.id),
                                             ('of_periode_ids', 'in', [period_categ.periode_id.id]),
                                             '|',
                                             ('user_id', '=', period_categ.technicien_id.user_id.id),
                                             ('of_user_id', '=', period_categ.technicien_id.user_id.id)])
                    rest = sum(tasks.mapped('of_periode_time_ids').filtered(
                        lambda t: t.periode_id.id == period_categ.periode_id.id and
                        t.user_id == period_categ.technicien_id.user_id).mapped('temps_affecte'))
            period_categ.temps_restant = period_categ.temps_prevu - rest
        return


class OfAffectationTache(models.Model):
    _name = "of.affectation.tache"

    tache_id = fields.Many2one('project.task', string="tache")
    periode_id = fields.Many2one('of.periode.planifiee', string=u"Période")
    temps_affecte = fields.Float(string=u"Temps affecté")
    name = fields.Date(string="Nom", related="periode_id.premier_jour")
    temps_effectue = fields.Float(string=u"Temps effectué", compute="_compute_temps")
    user_id = fields.Many2one(comodel_name='res.users', string=u"Technicien")

    @api.depends('tache_id', 'tache_id.timesheet_ids')
    def _compute_temps(self):
        """ Permet de calculer le temps effectué sur la période
        """
        for time_periode in self:
            records = time_periode.tache_id.timesheet_ids.filtered(
                lambda ts: time_periode.periode_id.premier_jour <= ts.date <= time_periode.periode_id.dernier_jour)
            time_periode.temps_effectue = sum(records.mapped('unit_amount'))
        return


class ProjectTask(models.Model):
    _inherit = "project.task"

    of_periode_ids = fields.Many2many('of.periode.planifiee', string=u"Période(s)")
    of_periode_time_ids = fields.One2many('of.affectation.tache', 'tache_id', string=u"Temps par période")
    of_time_left = fields.Float(string=u"Temps à affecter", compute="_compute_temps_restant")
    planned_hours = fields.Float(compute='_compute_planned_hours', inverse='_inverse_planned_hours', store=True)
    of_planned_dev_hours = fields.Float(string=u"Heures de développement")
    of_planned_review_hours = fields.Float(string=u"Heures de revue")
    project_id = fields.Many2one(required=True)

    @api.depends('of_periode_time_ids', 'planned_hours')
    def _compute_temps_restant(self):
        """ Permet le calcul du temps restant à affecter aux périodes
        """
        for task in self:
            task.of_time_left = task.planned_hours - sum(task.of_periode_time_ids.mapped('temps_affecte'))

    @api.depends('of_planned_dev_hours', 'of_planned_review_hours')
    def _compute_planned_hours(self):
        for task in self:
            task.planned_hours = task.of_planned_dev_hours + task.of_planned_review_hours

    @api.multi
    def _inverse_planned_hours(self):
        for task in self:
            task.of_planned_dev_hours = task.planned_hours
            task.of_planned_review_hours = 0

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
        picks = self.search(domain + args, limit=limit)
        return picks.name_get()

    def _get_infos_on_periode(self, periode, user):
        """ Récupère les informations des périodes en fonction de l'utilisateur
        affecté a la tâche et de la catégorie de la tâche
        """
        vals = {'periode_id': periode.id, 'user_id': user.id}
        user_periode = periode.technicien_ids.filtered(lambda t: t.user_id.id == user.id)
        categ_user = user_periode.category_ids.filtered(lambda c: c.categorie_id.id == self.categ_id.id)
        vals["temps_affecte"] = self.of_time_left if self.of_time_left <= categ_user.temps_restant \
            else categ_user.temps_restant
        return vals

    @api.onchange('planned_hours', 'of_periode_ids')
    def onchange_time(self):
        """ Change le temps affecté aux périodes si on ajoute une période
        ou modification des heures prévues (mettre le plus d'heures possible
        sur la première période, etc...)
        """
        records = self.of_periode_time_ids
        dev_time = self.of_planned_dev_hours
        review_time = self.of_planned_review_hours
        while records:
            first_date = min(records.mapped('name'))
            temp = records.filtered(lambda r: r.name == first_date)
            # Développeur
            if self.user_id:
                dev_temp = temp.filtered(lambda t: t.user_id.id == self.user_id.id)
                dev_user_periode = dev_temp.periode_id.technicien_ids.filtered(lambda t: t.user_id.id == self.user_id.id)
                dev_categ_user = dev_user_periode.category_ids.filtered(lambda c: c.categorie_id.id == self.categ_id.id)
                dev_temp.temps_affecte = 0
                tmp_dev_time = dev_time if dev_time <= dev_categ_user.temps_restant else dev_categ_user.temps_restant
                dev_temp.temps_affecte = tmp_dev_time
                dev_time -= tmp_dev_time
                records -= dev_temp
            # Relecteur
            if self.of_user_id:
                review_temp = temp.filtered(lambda t: t.user_id.id == self.of_user_id.id)
                review_user_periode = review_temp.periode_id.technicien_ids.filtered(
                    lambda t: t.user_id.id == self.of_user_id.id)
                review_categ_user = review_user_periode.category_ids.filtered(
                    lambda c: c.categorie_id.id == self.categ_id.id)
                review_temp.temps_affecte = 0
                tmp_review_time = review_time if review_time <= review_categ_user.temps_restant else \
                    review_categ_user.temps_restant
                review_temp.temps_affecte = tmp_review_time
                review_time -= tmp_review_time
                records -= review_temp
        return

    @api.onchange('of_periode_ids', 'user_id', 'of_user_id')
    def onchange_periode_ids(self):
        """ Ajoute ou enlève la possibilité de définir du temps par période
        """
        affectation_obj = self.env['of.affectation.tache']
        # Période du développeur
        dev_period_time = affectation_obj
        if self.user_id:
            to_add = affectation_obj
            if self.of_periode_ids:
                self.date_start = min(self.of_periode_ids.mapped('premier_jour'))
                self.date_end = max(self.of_periode_ids.mapped('dernier_jour'))
                already_used = self.of_periode_time_ids.filtered(
                    lambda t: t.user_id == self.user_id).mapped('periode_id').mapped('id')
                for periode in self.of_periode_ids:
                    if periode.id in already_used:
                        continue
                    to_add += affectation_obj.new(self._get_infos_on_periode(periode, self.user_id))
            dev_period_time = self.of_periode_time_ids.filtered(
                lambda t: t.periode_id in self.of_periode_ids and t.user_id == self.user_id) + to_add
        # Période du relecteur
        review_period_time = affectation_obj
        if self.of_user_id:
            to_add = affectation_obj
            if self.of_periode_ids:
                self.date_start = min(self.of_periode_ids.mapped('premier_jour'))
                self.date_end = max(self.of_periode_ids.mapped('dernier_jour'))
                already_used = self.of_periode_time_ids.filtered(
                    lambda t: t.user_id == self.of_user_id).mapped('periode_id').mapped('id')
                for periode in self.of_periode_ids:
                    if periode.id in already_used:
                        continue
                    to_add += affectation_obj.new(self._get_infos_on_periode(periode, self.of_user_id))
            review_period_time = self.of_periode_time_ids.filtered(
                lambda t: t.periode_id in self.of_periode_ids and t.user_id == self.of_user_id) + to_add
        self.of_periode_time_ids = dev_period_time + review_period_time
