# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import ValidationError


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    tournee_ids = fields.Many2many(
        'of.planning.tournee', 'of_planning_intervention_of_planning_tournee_rel', 'intervention_id', 'tournee_id',
        compute='_compute_tournee_ids', store=True, string='Planification')

    # @api.depends

    @api.multi
    @api.depends('employee_ids', 'date', 'tournee_ids.date', 'tournee_ids.employee_id', 'state')
    def _compute_tournee_ids(self):
        tournee_obj = self.env['of.planning.tournee']
        for intervention in self:
            if intervention.employee_ids and intervention.date\
                    and intervention.state in ('draft', 'confirm', 'done', 'unfinished'):
                tournees = tournee_obj.search([
                    ('employee_id', 'in', intervention.employee_ids.ids),
                    ('date', '=', intervention.date[:10])])
                intervention.tournee_ids = [(5, 0, 0)] + [(4, le_id, 0) for le_id in tournees._ids]

    # @api.onchange

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

    # Héritages

    @api.model
    def create(self, vals):
        """Vérifie qu'aucun des intervenants n'a sa tournée du jour bloquée, créé les tournées si nécessaire"""
        planning_tournee_obj = self.env['of.planning.tournee']

        # On verifie que la tournée n'est pas déjà complète ou bloquée.
        date_jour = isinstance(vals['date'], basestring) and vals['date'][:10] or vals['date'].strftime('%Y-%m-%d')

        # vals['employee_ids'] est un code 6 sur création et est toujours renseigné car champ obligatoire
        employee_ids_val = vals.get('employee_ids', [(6, 0, [])])
        employee_ids = \
            employee_ids_val[0][2] if employee_ids_val[0][0] == 6\
            else [val[1] for val in employee_ids_val if val[0] == 4]

        planning_tournees = planning_tournee_obj.search([('date', '=', date_jour),
                                                         ('employee_id', 'in', employee_ids)])
        tournees_bloquees = planning_tournees.filtered(lambda t: t.is_bloque)

        if tournees_bloquees:
            raise ValidationError(u'Un des intervenants a déjà une tournée bloquée à cette date.')

        intervention = super(OfPlanningIntervention, self).create(vals)
        if len(planning_tournees) != len(employee_ids):  # Une ou plusieurs tournées n'ont pas encore été créées.
            intervention.create_tournees()
            intervention._recompute_todo(self._fields['tournee_ids'])
        return intervention

    @api.multi
    def write(self, vals):
        intervention_sudo_obj = self.env['of.planning.intervention'].sudo()
        old_data = {}
        if 'date' in vals or 'employee_ids' in vals or 'state' in vals:
            if 'date' in vals or 'employee_ids' in vals:
                if self.mapped('tournee_ids').filtered('is_bloque'):
                    raise ValidationError(u"La tournée d'un des intervenants est bloquée")

            # Vérification des tournées à supprimer
            for intervention in self:
                employee_ids = old_data.setdefault(intervention.date_date, set())
                employee_ids |= set(intervention.employee_ids.ids)

        super(OfPlanningIntervention, self).write(vals)

        if old_data:
            if 'date' in vals or 'employee_ids' in vals:
                if self.mapped('tournee_ids').filtered('is_bloque'):
                    raise ValidationError(u"Un des intervenants a déjà une tournée bloquée sur ce créneau")
            for date, employee_ids in old_data.iteritems():
                intervention_sudo_obj.remove_tournees(date, employee_ids)

        for intervention in self:
            # La vérif de nécessité de création de tournée est faite directement dans la fonction create_tournees
            intervention.create_tournees()
            intervention._recompute_todo(self._fields['tournee_ids'])

        return True

    @api.multi
    def unlink(self):
        interventions = [(intervention.date_date, intervention.employee_ids.ids) for intervention in self]
        super(OfPlanningIntervention, self).unlink()
        for date, employee_ids in interventions:
            # la vérif de nécessité de suppression de tournée est faite directement dans la fonction remove_tournee
            self.sudo().remove_tournees(date, employee_ids)
        return True

    # Autres

    @api.multi
    def create_tournees(self):
        """
        Crée les tournées des employés de cette intervention si besoin
        C'est à dire si il n'y a pas de tournée et que l'intervention n'est ni annulée ni reportée
        :return: liste des tournées créées
        """
        self.ensure_one()
        res = []
        if self.state in ('cancel', 'postponed'):
            return res
        tournee_obj = self.env['of.planning.tournee']
        date_intervention = self.date_date
        address = self.address_id
        ville = address

        for employee in self.employee_ids:
            tournee = tournee_obj.search([('date', '=', date_intervention), ('employee_id', '=', employee.id)], limit=1)
            if not tournee:
                tournee_data = {
                    'date'       : date_intervention,
                    'employee_id': employee.id,
                    'epi_lat'    : ville.geo_lat,
                    'epi_lon'    : ville.geo_lng,
                    'is_bloque'  : False,
                    'is_confirme': False
                }
                res.append(tournee_obj.create(tournee_data))
        return res

    @api.model
    def remove_tournees(self, date, employee_ids):
        """
        Vérifie le tournées des employés renseignés à une date et supprime celle qui n'ont aucun RDV.
        :param date: date à vérifier
        :param employee_ids: list des ids des employés à vérifier
        :return: True
        """
        date = date and date[:10] or date.strftime('%Y-%m-%d')
        planning_tournee_obj = self.env['of.planning.tournee']
        employees_tournees_unlink_ids = []
        for employee_id in employee_ids:
            planning_intervention = self.search([
                ('date_date', '=', date),
                ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                ('employee_ids', 'in', employee_id)], limit=1)
            if not planning_intervention:
                # Il n'existe plus de plannings pour la tournee, on la supprime
                employees_tournees_unlink_ids.append(employee_id)

        tournees_unlink = planning_tournee_obj.search(
            [('date', '=', date), ('employee_id', 'in', employees_tournees_unlink_ids),
             ('is_bloque', '=', False), ('is_confirme', '=', False),
             ('address_depart_id', '=', False), ('address_retour_id', '=', False), ('secteur_id', '=', False)])
        return tournees_unlink.unlink()

    @api.multi
    def _calc_new_description(self):
        """Ajoute la tache et les notes du service à la description"""
        self.ensure_one()
        if self.service_id:
            infos = (
                self.tache_id.name,
                self.service_id.note
            )
            description = self.description or ""
            res = [info for info in infos if (info and info not in description)]
            self.description = description + " ".join(res)


class OfPlanningEquipe(models.Model):  #@todo: vérifier si nécessaire
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

    date = fields.Date(string='Date', required=True)
    date_jour = fields.Char(compute="_compute_date_jour", string="Jour")
    # Champ equipe_id avant la refonte du planning nov. 2019.
    # Conservé quelques jours pour la transtion des données.
    # À supprimer par la suite.
    equipe_id = fields.Many2one('of.planning.equipe', string=u'Équipe')
    employee_id = fields.Many2one('hr.employee', string=u'Intervenant', required=True, ondelete='cascade')
    employee_other_ids = fields.Many2many(
        'hr.employee', 'tournee_employee_other_rel', 'tournee_id', 'employee_id', string=u'Équipiers', required=True,
        domain="['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]")
    secteur_id = fields.Many2one('of.secteur', string='Secteur', domain="[('type', 'in', ['tech', 'tech_com'])]")
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

    _sql_constraints = [
        ('date_employee_uniq', 'unique (date,employee_id)',
         u"Il ne peut exister qu'une tournée par employé pour un jour donné")
    ]

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

                end_local = fields.Datetime.context_timestamp(
                    self, fields.Datetime.from_string(intervention.date_deadline))
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

        # @todo: vérifier pertinence du champ is_bloque avec aymeric
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


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    of_tournee_ids = fields.One2many('of.planning.tournee', 'employee_id', string=u"Tournées")


class OFHoraireSegment(models.Model):
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
        res = super(OFHoraireSegment, self).create(vals)
        self.recompute_is_complet_tournee(employee_id, deb, fin)
        return res

    @api.multi
    def write(self, vals):
        employee_id = vals.get('employee_id') or self.employee_id and self.employee_id.id
        deb = min(vals.get('date_deb', self.date_deb), self.date_deb)
        fin = max(vals.get('date_fin', self.date_fin), self.date_fin)
        res = super(OFHoraireSegment, self).write(vals)
        self.recompute_is_complet_tournee(employee_id, deb, fin)
        return res

    @api.model
    def unlink(self):
        employee_id = self.employee_id and self.employee_id.id
        deb = self.date_deb
        fin = self.date_fin
        res = super(OFHoraireSegment, self).unlink()
        self.recompute_is_complet_tournee(employee_id, deb, fin)
        return res
