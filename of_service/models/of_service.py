# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import date
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class OfService(models.Model):
    _name = "of.service"
    _inherit = "of.map.view.mixin"
    _description = "Service"

    @api.model_cr_context
    def _auto_init(self):
        # A SUPRIMER
        # Mise à jour du champ company_id des services existants
        cr = self._cr
        fill_company_id = False
        if self._auto:
            cr.execute("SELECT * FROM information_schema.columns WHERE table_name = 'of_service' AND column_name = 'company_id'")
            fill_company_id = not bool(cr.fetchall())

        res = super(OfService, self)._auto_init()
        if fill_company_id:
            cr.execute("UPDATE of_service AS s "
                       "SET company_id = p.company_id\n"
                       "FROM res_partner AS p\n"
                       "WHERE p.id = s.partner_id")
        return res

    def _default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    @api.one
    @api.depends('tache_id', 'address_id')
    def _compute_planning_ids(self):
        planning_obj = self.env['of.planning.intervention']
        for service in self:
            plannings = planning_obj.search([('tache_id', '=', service.tache_id.id),
                                             ('address_id', '=', service.address_id.id)], order='date desc')
            service.planning_ids = plannings
            service.date_last = plannings and plannings[0].date or False

    @api.model
    def _search_last_date(self, operator, operand):
        cr = self._cr

        query = ("SELECT s.id\n"
                 "FROM of_service AS s\n"
                 "LEFT JOIN of_planning_intervention AS p\n"
                 "  ON p.address_id = s.address_id\n"
                 "  AND p.tache_id = s.tache_id\n")

        if operand:
            if len(operand) == 10:
                # Copié depuis osv/expression.py
                if operator in ('>', '<='):
                    operand += ' 23:59:59'
                else:
                    operand += ' 00:00:00'
            query += ("GROUP BY s.id\n"
                      "HAVING MAX(p.date) %s '%s'" % (operator, operand))
        else:
            if operator == '=':
                query += "WHERE p.id IS NULL"
            else:
                query += "WHERE p.id IS NOT NULL"
        cr.execute(query)
        rows = cr.fetchall()
        return [('id', 'in', rows and zip(*rows)[0])]

    @api.multi
    @api.depends('date_next')
    def _compute_color(self):
        u""" COULEURS :
        Gris  : service dont l'adresse n'a pas de coordonnées GPS, ou service inactif
        Orange: service dont la date de prochaine intervention est dans moins d'un mois
        Rouge : service dont la date de prochaine intervention est inférieure à la date courante (ou à self._context.get('date_next_max'))
        Noir  : autres services
        """
        date_next_max = fields.Date.from_string(self._context.get('date_next_max') or fields.Date.today())

        for service in self:
            date_next = fields.Date.from_string(service.date_next)
            if not (service.address_id.geo_lat or service.address_id.geo_lng) or not service.active:
                service.color = 'gray'
            elif date_next <= date_next_max:
                service.color = 'red'
            elif date_next <= date_next_max + timedelta(days=30):
                service.color = 'orange'
            else:
                service.color = 'black'

    @api.model
    def get_color_map(self):
        u"""
        fonction pour la légende de la vue map
        """
        title = "Prochaine Intervention"
        v0 = {'label': "Plus d'un mois", 'value': 'black'}
        v1 = {'label': u'Ce mois-ci', 'value': 'orange'}
        v2 = {'label': u'En retard', 'value': 'red'}
        return {"title": title, "values": (v0, v1, v2)}

    # template_id = fields.Many2one('of.mail.template', string='Contrat')
    partner_id = fields.Many2one('res.partner', string='Partenaire', required=True, ondelete='restrict')
    address_id = fields.Many2one('res.partner', string="Adresse", ondelete='restrict')
    secteur_tech_id = fields.Many2one(related='address_id.secteur_tech_id', readonly=True)
    company_id = fields.Many2one('res.company', string=u"Société")

    # Champs ajoutés pour la vue map
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')
    precision = fields.Selection(related='address_id.precision')
    partner_name = fields.Char(related='partner_id.name')
    partner_mobile = fields.Char(related='partner_id.mobile')
    partner_phone = fields.Char(related='partner_id.phone')

    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    name = fields.Char(u"Libellé", compute="_compute_name", store=True)
    tag_ids = fields.Many2many('of.service.tag', string=u"Étiquettes")
    tache_name = fields.Char(related="tache_id.name", readonly=True)
    duree = fields.Float(string=u"Durée estimée")

    origin = fields.Char(string="Origine")

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois')
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours', default=_get_default_jours)

    note = fields.Text('Notes')
    date_next = fields.Date('Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention", required=True)
    date_fin = fields.Date(u"Date d'échéance")

    # Partner-related fields
    address_zip = fields.Char('Code Postal', size=24, related='address_id.zip', oldname="partner_zip")
    address_city = fields.Char('Ville', related='address_id.city', oldname="partner_city")

    recurrence = fields.Boolean(string=u"Récurrent?", default=True)
    recurring_rule_type = fields.Selection([
        #('daily', 'Jour(s)'),
        ('weekly', 'Semaine(s)'),
        ('monthly', 'Mois'),
        ('yearly', u'Année(s)'),
        ], string=u'Récurrence', default='yearly', help=u"Spécifier l'intervalle pour le calcul automatique de date de prochaine intervention dans les services.")
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1, help=u"Répéter (Jours/Semaines/Mois/Années)")

    state = fields.Selection([
        ('progress', 'En cours'),  #services récurrents
        ('todo', u'À faire'),  # services ponctuels
        ('done', u'fait'),  # services ponctuels
        ('cancel', u'Annulé'),  # services ponctuels et recurrents
        ], u'État')
    active = fields.Boolean(string="Active", default=True)

    planning_ids = fields.One2many('of.planning.intervention', compute='_compute_planning_ids', string="Interventions")
    date_last = fields.Date(
        string=u'Dernière intervention', compute='_compute_planning_ids', search='_search_last_date',
        help=u"Date de la dernière intervention")

    # Champs de recherche
    date_fin_min = fields.Date(string=u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date(string=u"Date échéance max", compute='lambda *a, **k:{}')
    date_controle = fields.Date(string=u"Date de contrôle", compute='lambda *a, **k:{}')

    # Couleur de contrôle
    color = fields.Char(compute='_compute_color', string='Couleur', store=False)

    @api.multi
    @api.depends('address_id', 'partner_id', 'tache_id')
    def _compute_name(self):
        for service in self:
            partner_name = service.partner_id and service.partner_id.name or u''
            address_zip = service.address_id and service.address_id.zip or u''
            tache_name = service.tache_id and service.tache_id.name or u''
            service.name = tache_name + partner_name + address_zip

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.ensure_one()
        if self.partner_id:
            self.address_id = self.partner_id
            self.company_id = self.partner_id.company_id

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        self.ensure_one()
        if self.tache_id:
            self.recurrence = self.tache_id.recurrence
            self.recurring_rule_type = self.tache_id.recurring_rule_type
            self.recurring_interval = self.tache_id.recurring_interval
            self.duree = self.tache_id.duree

    @api.onchange('date_next')
    def _onchange_date_next(self):
        # Remplissage automatique du mois en fonction de la date de prochaine intervention choisie
        # /!\ Un simple clic sur le champ date appelle cette fonction, et génère le mois avec la date courante
        #       avant que l'utilisateur ait confirmé son choix.
        #     Cette fonction doit donc être autorisée à écraser le mois déjà saisi
        #     Pour éviter les ennuis, elle est donc restreinte à un usage en mode création de nouveau service uniquement
        if self.date_next and not self._origin:  # <- signifie mode creation
            mois = self.env['of.mois'].search([('numero', '=', int(self.date_next[5:7]))])
            mois_id = mois[0] and mois[0].id or False
            if mois_id:
                self.mois_ids = [(4, mois_id, 0)]

    @api.multi
    def get_next_date(self, date_str):
        self.ensure_one()
        if self.recurrence:
            mois_nums = self.mois_ids.mapped('numero')

            d_date_from = fields.Date.from_string(max(date_str, self.date_last))
            d_date_next = d_date_from + self.get_relative_delta(self.recurring_rule_type, self.recurring_interval)

            date_mois = d_date_next.month
            date_annee = d_date_next.year

            if (date_mois not in mois_nums) and (date_mois+1 in mois_nums):
                # Le rdv a été pris en avance pour le mois suivant
                date_mois += 1

            mois = min(mois_nums, key=lambda m: (m <= date_mois, m))
            annee = date_annee + (mois <= date_mois)
            return fields.Date.to_string(date(annee, mois, 1))
        else:
            return False

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        #elif recurring_rule_type == 'daily':
        #    return relativedelta(days=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval)
        else:
            return relativedelta(years=interval)

    @api.multi
    def toggle_recurrence(self):
        return self.write({'recurrence': not self.recurrence})


    @api.model
    def create(self, vals):
        if vals.get('address_id') and not vals.get('partner_id'):
            address = self.env['res.partner'].browse(vals['address_id'])
            partner = address.parent_id or address
            vals['partner_id'] = partner.id
        return super(OfService, self).create(vals)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(OfService, self).search(args, offset, limit, order, count)
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(OfService, self).read(fields, load)
        return res

class OFServiceTag(models.Model):
    _name = 'of.service.tag'
    _description = u"Étiquettes des services"

    name = fields.Char(string=u"Libellé", required=True)
    active = fields.Boolean(string='Actif', default=True)
    color = fields.Integer(string=u"Color index")

class OFPlanningTache(models.Model):
    _inherit = "of.planning.tache"

    service_ids = fields.One2many("of.service", "tache_id", string="Services")
    service_count = fields.Integer(compute='_compute_service_count')

    recurrence = fields.Boolean(u"Tâche récurrente?")
    recurring_rule_type = fields.Selection([
        ('weekly', 'Semaine(s)'),
        ('monthly', 'Mois'),
        ('yearly', u'Année(s)'),
        ], string=u'Récurrence', default='monthly', help=u"Spécifier l'intervalle pour le calcul automatique de date de prochaine intervention dans les services.")
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1, help=u"Répéter (Jours/Semaines/Mois/Années)")
    recurrence_display = fields.Char(string=u"Récurrence", compute="_compute_recurrence_display")

    @api.multi
    @api.depends('service_ids')
    def _compute_service_count(self):
        service_obj = self.env['of.service']
        for tache in self:
            tache.service_count = len(service_obj.search([('tache_id', '=', tache.id), ('recurrence', '=', True)]))

    @api.multi
    @api.depends('recurrence', 'recurring_interval', 'recurring_rule_type')
    def _compute_recurrence_display(self):
        for tache in self:
            display = False
            if tache.recurrence:
                feminin = tache.recurring_rule_type and tache.recurring_rule_type == 'weekly' or False
                if feminin:
                    display = u"Toutes les "
                else:
                    display = u"Tous les "
                if tache.recurring_interval and tache.recurring_interval != 1:
                    display += chr(tache.recurring_interval) + u" "
                #if tache.recurring_rule_type == 'daily':
                #    display += u"jours"
                elif tache.recurring_rule_type == 'weekly':
                    display += u"semaines"
                elif tache.recurring_rule_type == 'monthly':
                    display += u"mois"
                elif tache.recurring_rule_type == 'yearly':
                    display += u"ans"
            tache.recurrence_display = display

    @api.multi
    def get_next_date(self, date_str):
        self.ensure_one()
        if self.recurrence:
            date_from_da = fields.Date.from_string(date_str)
            date_next_da = date_from_da + self.get_relative_delta(self.recurring_rule_type, self.recurring_interval)

            return fields.Date.to_string(date_next_da)
        else:
            return False

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        #elif recurring_rule_type == 'daily':
        #    return relativedelta(days=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval)
        else:
            return relativedelta(years=interval)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """permet de montrer les tache recurrentes en premier ou les taches ponctuelles en premier"""
        rec_first = self._context.get('show_rec_icon_first', -1)
        if rec_first != -1:
            res = super(OFPlanningTache, self).name_search(name, args + [['recurrence', '=', rec_first]], operator, limit) or []
            limit = limit - len(res)
            res += super(OFPlanningTache, self).name_search(name, [['recurrence', '!=', rec_first]], operator, limit) or []
            return res
        return super(OFPlanningTache, self).name_search(name, args, operator, limit)


class OFPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    service_id = fields.Many2one('of.service', string="Service", domain="[('address_id', '=', address_id)]")

    @api.onchange('address_id', 'tache_id')
    def _onchange_address_id(self):
        super(OFPlanningIntervention, self)._onchange_address_id()
        if self.address_id and self.address_id.service_address_ids:
            if self.tache_id:
                service = self.address_id.service_address_ids.filtered(lambda x: x.tache_id == self.tache_id.id)
                self.service_id = service and service[0] or False
            else:
                self.service_id = self.address_id.service_address_ids[0]

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.tache_id = self.service_id.tache_id

    @api.multi
    def write(self, vals):
        res = super(OFPlanningIntervention, self).write(vals)
        if vals.get('state', False) == 'done':
            for intervention in self:
                if intervention.service_id:
                    if intervention.service_id.recurrence:
                        intervention.service_id.date_next = intervention.service_id.get_next_date(intervention.date_date)
                    else:
                        intervention.service_id.state = 'done'
        return res

    @api.model
    def create(self, vals):
        intervention = super(OFPlanningIntervention, self).create(vals)
        if vals.get('state', False) == 'done':
            if intervention.service_id:
                if intervention.service_id.recurrence:
                    intervention.service_id.date_next = intervention.service_id.get_next_date(intervention.date_date)
                else:
                    intervention.service_id.state = 'done'
        return intervention

class ResPartner(models.Model):
    _inherit = "res.partner"

    service_address_ids = fields.One2many('of.service', 'address_id', string='Services', context={'active_test': False})
    service_partner_ids = fields.One2many('of.service', 'partner_id', string='Services du partenaire', context={'active_test': False},
                                          help="Services liés au partenaire, incluant les services des contacts associés")
