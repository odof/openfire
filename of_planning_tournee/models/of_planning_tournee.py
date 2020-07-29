# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError

import math
from math import asin, sin, cos, sqrt

def distance_points(lat1, lon1, lat2, lon2):
    u"""
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param *: Coordonnées gps en degrés
    """
    lat1, lon1, lat2, lon2 = [math.radians(v) for v in (lat1, lon1, lat2, lon2)]
    return 2*asin(sqrt((sin((lat1-lat2)/2)) ** 2 + cos(lat1)*cos(lat2)*(sin((lon1-lon2)/2)) ** 2)) * 6366

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    tournee_ids = fields.Many2many('of.planning.tournee', 'of_planning_intervention_of_planning_tournee_rel', 'intervention_id', 'tournee_id', compute='_compute_tournee_ids', store=True, string='Planification')

    @api.multi
    @api.depends('employee_ids', 'date', 'tournee_ids.date', 'tournee_ids.employee_id')
    def _compute_tournee_ids(self):
        tournee_obj = self.env['of.planning.tournee']
        for intervention in self:
            if intervention.employee_ids and intervention.date:
                tournees = tournee_obj.search([('employee_id', 'in', intervention.employee_ids._ids), ('date', '=', intervention.date[:10])])
                intervention.tournee_ids = [(5, 0, 0)] + [(4, le_id, 0) for le_id in tournees._ids]

    @api.multi
    def create_tournees(self):
        """Créer les tournées des employés de cette intervention si besoin"""
        self.ensure_one()
        tournee_obj = self.env['of.planning.tournee']
        date_intervention = self.date
        date_jour = isinstance(date_intervention, basestring) and date_intervention[:10] or date_intervention.strftime('%Y-%m-%d')
        address = self.address_id
        ville = address
        country = address.country_id
        res = []
        for employee in self.employee_ids:
            tournee = tournee_obj.search([('date', '=', date_jour), ('employee_id', '=', employee.id)], limit=1)
            if not tournee:
                tournee_data = {
                    'date'       : date_jour,
                    'employee_id': employee.id,
                    'epi_lat'    : ville.geo_lat,
                    'epi_lon'    : ville.geo_lng,
                    # 'adr_id'     : address.id,
                    # 'zip'        : ville.zip,
                    # 'city'       : ville.city,
                    # 'country_id' : country and country.id,
                    'is_bloque'  : False,
                    'is_confirme': False
                }
                res.append(tournee_obj.create(tournee_data))
        return res

    @api.model
    def remove_tournees(self, date, employees):
        date = date and date[:10] or date.strftime('%Y-%m-%d')
        planning_tournee_obj = self.env['of.planning.tournee']
        employees_tournees_unlink_ids = []
        for employee in employees:
            planning_intervention_ids = self.search([('date', '>=', date), ('date', '<=', date), ('employee_ids', 'in', employee.id)], limit=1)
            if not planning_intervention_ids:
                # Il n'existe plus de plannings pour la tournee, on la supprime
                employees_tournees_unlink_ids.append(employee.id)

        tournees_unlink = planning_tournee_obj.search([('date', '=', date), ('employee_id', 'in', employees_tournees_unlink_ids),
                                                       ('is_bloque', '=', False), ('is_confirme', '=', False)])
        tournees_unlink.unlink()

    @api.model
    def create(self, vals):
        planning_tournee_obj = self.env['of.planning.tournee']

        # On verifie que la tournée n'est pas déjà complète ou bloquée.
        date_jour = isinstance(vals['date'], basestring) and vals['date'][:10] or vals['date'].strftime('%Y-%m-%d')

        if not vals.get('employee_ids', False):
            raise UserError(u"Cette intervnetion n'a pas d'intervenant")
        employee_ids_val = vals.get('employee_ids', False)#[0][2]  # vals['employee_ids'] est un code 6 sur création et est toujours renseigné car champ obligatoire
        employee_ids = employee_ids_val[0][0] == 6 and employee_ids_val[0][2] or [le_tup[1] for le_tup in employee_ids_val if le_tup[0] == 4]

        planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                            ('employee_id', 'in', employee_ids),
                                                            ('is_bloque', '=', True)])
        if planning_tournee_ids:
            raise ValidationError(u'Un des intervenants a déjà une tournée bloquée à cette date.')

        intervention = super(OfPlanningIntervention, self).create(vals)
        planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                            ('employee_id', 'in', employee_ids)])
        if len(planning_tournee_ids) != len(employee_ids):  # Une ou plusieurs tournées n'ont pas encore été créées.
            intervention.create_tournees()
            intervention._recompute_todo(self._fields['tournee_ids'])
        return intervention

    @api.multi
    def write(self, vals):
        planning_tournee_obj = self.env['of.planning.tournee']
        intervention_obj = self.env['of.planning.intervention']
        if 'date' in vals or 'employee_ids' in vals:
            for intervention in self:
                date = vals.get('date', intervention.date)
                date_jour = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
                employee_ids = set(intervention.employee_ids._ids)
                for row in vals.get('employee_ids', []):
                    if row[0] == 5:
                        employee_ids = set()
                    elif row[0] == 2:
                        employee_ids.discard(row[1])
                    elif row[0] == 4:
                        employee_ids.add(row[1])
                    elif row[0] == 6:
                        employee_ids = set(row[2])
                ajoute_ids = employee_ids - set(intervention.employee_ids.ids)
                retire_ids = set(intervention.employee_ids.ids) - employee_ids
                concernes_ids = (vals.get('employee_ids', False) and ajoute_ids | retire_ids) or employee_ids  # si pas de modif employee_ids mais modif date
                bloque_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                          ('employee_id', 'in', list(concernes_ids)),
                                                          ('is_bloque', '=', True)])
                if bloque_ids:
                    raise ValidationError(u'Un des intervenants a déjà une tournée bloquée sur ce créneau')

                intervention_retires_ids = intervention_obj.search([('employee_ids', 'in', list(retire_ids))])
                intervention_obj.sudo().remove_tournees(intervention.date, intervention_retires_ids)

        super(OfPlanningIntervention, self).write(vals)

        for intervention in self:
            intervention.create_tournees()
            intervention._recompute_todo(self._fields['tournee_ids'])
        return True

    @api.multi
    def unlink(self):
        interventions = []
        for intervention in self:
            date = intervention.date
            date_jour = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
            interventions.append((date_jour, intervention.employee_ids))
        super(OfPlanningIntervention, self).unlink()
        for date, employee_ids in interventions:
            self.sudo().remove_tournees(date, employee_ids)
        return True

    @api.multi
    def _calc_new_description(self):
        self.ensure_one()

        tache = self.tache_id
        for service in self.address_id.service_address_ids:
            if service.tache_id == tache:
                infos = (
                    self.description,
                    tache.name,
                    # service.template_id and service.template_id.name,
                    service.note
                )
                res = [info for info in infos if info]
                self.description = "\n".join(res)

    @api.onchange('address_id')
    def _onchange_address_id(self):
        super(OfPlanningIntervention, self)._onchange_address_id()
        if self.address_id and self.tache_id:
            self._calc_new_description()

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        super(OfPlanningIntervention, self)._onchange_tache_id()
        if self.partner_id and self.tache_id:
            self._calc_new_description()
        # auto-détection du service
        if not self.address_id:
            # ne pas charger un service si il n'y a pas d'adresse
            return
        service_obj = self.env['of.service']
        vals = {'service_id': False}
        if self.tache_id:
            if self.service_id and self.service_id.tache_id.id == self.tache_id.id:
                del vals['service_id']
            else:
                service = service_obj.search(['|',
                                                ('address_id', '=', self.address_id.id),
                                                ('partner_id', '=', self.partner_id.id),
                                              ('tache_id', '=', self.tache_id.id)], limit=1)
                if service:
                    vals['service_id'] = service

        self.update(vals)

class OfPlanningEquipe(models.Model):
    _inherit = "of.planning.equipe"

    address_id = fields.Many2one('res.partner', string=u'Adresse de départ')
    address_retour_id = fields.Many2one('res.partner', string='Adresse de retour')
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        if self.employee_ids:
            self.address_id = self.employee_ids[0].address_home_id
            self.address_retour_id = self.address_id

    @api.onchange('address_id')
    def _onchange_address_id(self):
        if self.address_id:
            self.address_retour_id = self.address_id

class OfPlanningTournee(models.Model):
    _name = "of.planning.tournee"
    _description = u"Tournée"
    _order = 'date DESC'
    _rec_name = 'date'

    _sql_constraints = [
        ('date_employee_uniq', 'unique (date,employee_id)', u"Il ne peut exister qu'une tournée par employé pour un jour donné")
    ]

    date = fields.Date(string='Date', required=True)
    date_jour = fields.Char(compute="_compute_date_jour", string="Jour")
    # Champ equipe_id avant la refonte du planning nov. 2019.
    # Conservé quelques jours pour la transtion des données.
    # À supprimer par la suite.
    equipe_id = fields.Many2one('of.planning.equipe', string=u'Équipe')
    employee_id = fields.Many2one('hr.employee', string=u'Intervenant', required=True)
    employee_other_ids = fields.Many2many(
        'hr.employee', 'tournee_employee_other_rel', 'tournee_id', 'employee_id', string=u'Équipiers', required=True,
        domain="[('of_est_intervenant', '=', True)]")
    secteur_id = fields.Many2one('of.secteur', string='Secteur', domain="[('type', 'in', ['tech', 'tech_com'])]")
    #secteur_name = fields.Char(related="secteur_id.name")
    epi_lat = fields.Float(string=u'Épicentre Lat', digits=(12, 12))
    epi_lon = fields.Float(string=u'Épicentre Lon', digits=(12, 12))
    address_depart_id = fields.Many2one('res.partner', string=u'Adresse départ')
    address_retour_id = fields.Many2one('res.partner', string='Adresse retour')

    zip_id = fields.Many2one('res.better.zip', 'Ville')
    distance = fields.Float(string='Eloignement (km)', digits=(12, 4), default=20.0)
    is_complet = fields.Boolean(compute="_compute_is_complet", string='Complet', store=True)
    is_bloque = fields.Boolean(string=u'Bloqué', help=u'Journée bloquée : ne sera pas proposée à la planification')
    is_confirme = fields.Boolean(
        string=u'Confirmé', default=True,
        help=u'Une tournée non confirmée sera supprimée si on lui retire ses rendez-vous')
    date_min = fields.Date(related="date", string="Date min")
    date_max = fields.Date(related="date", string="Date max")
    intervention_ids = fields.Many2many(
        'of.planning.intervention', 'of_planning_intervention_of_planning_tournee_rel', 'tournee_id', 'intervention_id',
        string='Interventions')

    # @api.multi
    # @api.depends('employee_id', 'date')
    # def _compute_tournee_ids(self):
    #     intervention_obj = self.env['of.planning.intervention']
    #     for tournee in self:
    #         if tournee.employee_id and tournee.date:
    #             interventions = intervention_obj.search(
    #                     [('employee_ids', 'in', tournee.employee_id.id), ('date', '>=', tournee.date), ('date', '<=', tournee.date)])
    #             tournee.intervention_ids = [(6, 0, interventions.ids)]

    @api.model_cr_context
    def _auto_init(self):
        # Lors de la 1ère mise à jour après la refonte des planning (nov. 2019), on migre les données existantes.
        cr = self._cr
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_planning_tournee' AND column_name = 'employee_id'")
        existe_avant = bool(cr.fetchall())
        res = super(OfPlanningTournee, self)._auto_init()
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_planning_tournee' AND column_name = 'employee_id'")
        existe_apres = bool(cr.fetchall())
        # Si le champ employee_id n'existe pas avant et l'est après la mise à jour,
        # c'est que l'on est à la 1ère mise à jour après la refonte du planning, on doit faire la migration des données.
        if not existe_avant and existe_apres:
            # On supprime la colonne et les tables de l'ancienne planification.
            cr.execute("ALTER TABLE of_planning_intervention DROP COLUMN tournee_id")
            cr.execute("DROP TABLE of_tournee_planification, of_tournee_planification_partner, of_tournee_planification_planning")
            # On vide les tournées existantes et on les re-créer.
            cr.execute("TRUNCATE of_planning_intervention_of_planning_tournee_rel, tournee_employee_other_rel, of_planning_tournee")
            interventions = self.env['of.planning.intervention'].search([('state','not in',('cancel','postponed'))], order="date")
            for intervention in interventions:
                intervention.create_tournees()
            interventions._recompute_todo(interventions._fields['tournee_ids'])
        return res

    @api.depends('date')
    def _compute_date_jour(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for tournee in self:
            jour = ""
            if tournee.date:
                date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(tournee.date))
                jour = date_local.strftime("%A").capitalize()
            tournee.date_jour = jour

    @api.multi
    @api.depends('employee_id', 'date', 'is_bloque', 'employee_id.of_tz', 'employee_id.of_tz_offset')
    def _compute_is_complet(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        intervention_obj = self.env['of.planning.intervention']
        today_str = fields.Date.today()
        for tournee in self:
            if tournee.is_bloque:
                tournee.is_complet = False
                continue
            if tournee.date < today_str:
                tournee.is_complet = True
                continue
            employee = tournee.employee_id
            if employee.of_tz and employee.of_tz != 'Europe/Paris':
                self = self.with_context(tz=employee.of_tz)

            interventions = intervention_obj.search([
                ('employee_ids', 'in', employee.id),
                ('date', '<=', tournee.date),
                ('date_deadline', '>=', tournee.date),
                ('state', 'in', ('draft', 'confirm'))
            ], order="date")
            if not interventions:
                tournee.is_complet = False
                continue

            date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(tournee.date))
            horaires_emp = employee.get_horaires_date(tournee.date)[employee.id]
            nb_creneaux = len(horaires_emp)
            if nb_creneaux == 0:
                tournee.is_complet = True
                continue
            start_end_list = [(0, horaires_emp[0][0])]  # liste des créneaux non-travaillés de l'employé
            for i in range(1, nb_creneaux):
                start_end_list.append((horaires_emp[i-1][1], horaires_emp[i][0]))
            start_end_list.append((horaires_emp[-1][1], 24))
            debut_journee = horaires_emp[0][0]
            fin_journee = horaires_emp[-1][1]

            for intervention in interventions:
                start_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date))
                if start_local.day != date_local.day:
                    start_flo = debut_journee
                else:
                    start_flo = (start_local.hour +
                                 start_local.minute / 60 +
                                 start_local.second / 3600)

                end_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date_deadline))
                if end_local.day != date_local.day:
                    end_flo = fin_journee
                else:
                    end_flo = (end_local.hour +
                               end_local.minute / 60 +
                               end_local.second / 3600)

                start_end_list.append((start_flo, end_flo))
            start_end_list.sort()

            is_complet = True
            last_end = 0
            for s, e in start_end_list:
                if s - last_end > 0:
                    is_complet = False
                    break
                if e > last_end:
                    last_end = e
            tournee.is_complet = is_complet

    @api.multi
    def _get_dummy_fields(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for tournee in self:
            d = fields.Date.context_today(self)
            tournee.date_min = d
            tournee.date_max = d

    @api.onchange('zip_id')
    def _onchange_zip_id(self):
        if self.zip_id:
            self.epi_lat = self.zip_id.geo_lat
            self.epi_lon = self.zip_id.geo_lng

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.address_depart_id = self.employee_id.of_address_depart_id
            self.address_retour_id = self.employee_id.of_address_retour_id

    @api.onchange('address_depart_id')
    def _onchange_address_depart_id(self):
        if self.address_depart_id:
            self.address_retour_id = self.address_depart_id

    @api.model
    def create(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        if vals.get('is_bloque'):
            if intervention_obj.search([('date', '>=', vals['date']), ('date', '<=', vals['date']),
                                        ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                        ('employee_ids', 'in', vals['employee_id'])]):
                raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')
        return super(OfPlanningTournee, self).create(vals)

    @api.multi
    def write(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        for tournee in self:
            if vals.get('is_bloque', tournee.is_bloque):
                date_intervention = vals.get('date', tournee.date)
                employee_id = vals.get('employee_id', tournee.employee_id.id)
                if intervention_obj.search([('date', '>=', date_intervention), ('date', '<=', date_intervention),
                                            ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                            ('employee_ids', 'in', employee_id)]):
                    raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')
        return super(OfPlanningTournee, self).write(vals)


class OfPlanningRessourceConfig(models.Model):
    _name = "of.planning.ressource.config"
    #@TODO: auto-génerer les enregistrements

    quinzaine_id = fields.Many2one('date.range', string="Quinzaine") #@TODO: domain quinzaines civiles
    quinzaine_debut = fields.Date(compute="")
    quinzaine_fin = fields.Date(compute="")
    employee_id = fields.Many2one('hr.employee') #TODO domain

    tache_categ_id = fields.Many2one('of.planning.tache.categ')  # TODO domain

    nb_heures_total = fields.Integer(compute="")
    nb_heures_categ = fields.Integer()  # l'Utilisateur affecte ce champ
    nb_heures_non_planif = fields.Integer(compute="")



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    of_tournee_ids = fields.One2many('of.planning.tournee', 'employee_id', string=u"Tournées")

class OFHorairesSegment(models.Model):
    _inherit = 'of.horaire.segment'

    @api.model
    def recompute_is_complet_tournee(self, employee_id, deb=False, fin=False):
        tournee_obj = self.env['of.planning.tournee']
        if not deb:
            tournees = tournee_obj.search([('employee_id', '=', employee_id)])
        else:
            tournees_domain = [('employee_id', '=', employee_id), ('date', '>=', deb)]
            tournees_domain = fin and tournees_domain + [('date', '<=', fin)] or tournees_domain
            tournees = tournee_obj.search(tournees_domain)
        tournees._compute_is_complet()

    @api.model
    def create(self, vals):
        employee_id = vals.get('employee_id')
        deb = vals.get('date_deb')
        fin = vals.get('date_fin')
        res = super(OFHorairesSegment, self).create(vals)
        self.recompute_is_complet_tournee(employee_id, deb, fin)
        return res

    @api.multi
    def write(self, vals):
        employee_id = vals.get('employee_id') or self.employee_id and self.employee_id.id
        deb = min(vals.get('date_deb', self.date_deb), self.date_deb)
        fin = max(vals.get('date_fin', self.date_fin), self.date_fin)
        res = super(OFHorairesSegment, self).write(vals)
        self.recompute_is_complet_tournee(employee_id, deb, fin)
        return res

    @api.model
    def unlink(self):
        employee_id = self.employee_id and self.employee_id.id
        deb = self.date_deb
        fin = self.date_fin
        res = super(OFHorairesSegment, self).unlink()
        self.recompute_is_complet_tournee(employee_id, deb, fin)
        return res
