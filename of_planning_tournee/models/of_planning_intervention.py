# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, models, fields
from odoo.exceptions import ValidationError


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    tournee_ids = fields.Many2many(
        'of.planning.tournee', 'of_planning_intervention_of_planning_tournee_rel', 'intervention_id', 'tournee_id',
        compute='_compute_tournee_ids', store=True, string='Planification')
    map_color_tour = fields.Char(compute='_compute_tour_data', string='Color')
    tour_number = fields.Char(compute='_compute_tour_data', string='Tour number')
    # Time slots data
    duration_one_way = fields.Float(string='Duration one way (min)')
    distance_one_way = fields.Float(string='Distance one way (km)')
    return_duration = fields.Float(string='Return duration (min)')
    return_distance = fields.Float(string='Return distance (km)')

    # @api.depends

    @api.multi
    @api.depends('employee_ids', 'date', 'tournee_ids.date', 'tournee_ids.employee_id', 'state')
    def _compute_tournee_ids(self):
        tournee_obj = self.env['of.planning.tournee']
        for intervention in self:
            if intervention.employee_ids and intervention.date \
                    and intervention.state in ('draft', 'confirm', 'done', 'unfinished'):
                tournees = tournee_obj.search([
                    ('employee_id', 'in', intervention.employee_ids.ids),
                    ('date', '=', intervention.date[:10])])
                intervention.tournee_ids = [(5, 0, 0)] + [(4, le_id, 0) for le_id in tournees._ids]

    @api.multi
    def _compute_tour_data(self):
        if self._context.get('active_tour_id'):
            tour = self.env['of.planning.tournee'].browse(self._context.get('active_tour_id'))
            address_dict = {}
            for idx, inter in enumerate(tour.intervention_ids, 1):
                if not address_dict.get(inter.address_id.id):
                    address_dict[inter.address_id.id] = {inter: idx}
                else:
                    address_dict[inter.address_id.id][inter] = idx
            for rec in self:
                interventions_at_address = address_dict.get(rec.address_id.id)
                tour_number = ', '.join(map(str, interventions_at_address.values()))
                color = 'blue'
                rec.map_color_tour = color
                rec.tour_number = tour_number
        else:
            for rec in self:
                rec.map_color_tour = False
                rec.tour_number = False

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
        # La vérif de nécessité de création de tournée est faite directement dans la fonction create_tournees
        intervention.create_tournees()
        intervention._recompute_todo(self._fields['tournee_ids'])
        return intervention

    @api.multi
    def write(self, vals):
        intervention_sudo_obj = self.env['of.planning.intervention'].sudo()
        old_data = {}
        recompute_tournee_fields = self.get_recompute_tournee_fields()
        if any(field_name in vals for field_name in recompute_tournee_fields):
            if self.mapped('tournee_ids').filtered('is_bloque'):
                raise ValidationError(u"La tournée d'un des intervenants est bloquée")

            # Vérification des tournées à supprimer
            for intervention in self:
                for date_tournee in intervention.get_date_tournees():
                    employee_ids = old_data.setdefault(date_tournee, set())
                    employee_ids |= set(intervention.employee_ids.ids)

        res = super(OfPlanningIntervention, self).write(vals)

        if old_data:
            if ('date' in vals or 'employee_ids' in vals) and self.mapped('tournee_ids').filtered('is_bloque'):
                raise ValidationError(u"Un des intervenants a déjà une tournée bloquée sur ce créneau")
            for date_eval, employee_ids in old_data.iteritems():
                intervention_sudo_obj.remove_tournees([date_eval], employee_ids)

        for intervention in self:
            # La vérif de nécessité de création de tournée est faite directement dans la fonction create_tournees
            intervention.create_tournees()
            intervention._recompute_todo(self._fields['tournee_ids'])

        return res

    @api.multi
    def unlink(self):
        interventions = [(intervention.get_date_tournees(), intervention.employee_ids.ids) for intervention in self]
        super(OfPlanningIntervention, self).unlink()
        for date_list, employee_ids in interventions:
            # la vérif de nécessité de suppression de tournée est faite directement dans la fonction remove_tournee
            self.sudo().remove_tournees(date_list, employee_ids)
        return True

    # Autres

    @api.model
    def get_recompute_tournee_fields(self):
        return ['date', 'employee_ids', 'state']

    @api.multi
    def get_date_tournees(self):
        self.ensure_one()
        res = []
        date_deb_str = self.date_date
        date_fin_str = fields.Date.to_string(fields.Date.from_string(self.date_deadline))
        res.append(date_deb_str)
        # intervention sur plusieurs jours, prendre toutes les dates intermédiaires
        if date_fin_str != date_deb_str:
            date_fin_da = fields.Date.from_string(self.date_deadline)
            date_current_da = fields.Date.from_string(date_deb_str) + timedelta(days=1)
            while date_current_da <= date_fin_da:
                res.append(fields.Date.to_string(date_current_da))
                date_current_da += timedelta(days=1)
        return res

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
        dates_eval = self.get_date_tournees()
        address = self.address_id

        for employee in self.employee_ids:
            for date_eval in dates_eval:
                tournee = tournee_obj.search([('date', '=', date_eval), ('employee_id', '=', employee.id)], limit=1)
                if not tournee:
                    tournee_data = {
                        'date': date_eval,
                        'employee_id': employee.id,
                        'secteur_id': address.of_secteur_tech_id.id,
                        'epi_lat': address.geo_lat,
                        'epi_lon': address.geo_lng,
                        'is_bloque': False,
                        'is_confirme': False
                    }
                    res.append(tournee_obj.create(tournee_data))
                elif tournee.secteur_id != address.of_secteur_tech_id:
                    tournee.secteur_id = address.of_secteur_tech_id
        return res

    @api.model
    def remove_tournees(self, date_list, employee_ids):
        """
        Vérifie le tournées des employés renseignés à une date et supprime celle qui n'ont aucun RDV.
        :param date_list: liste de dates au format string à vérifier
        :param employee_ids: list des ids des employés à vérifier
        :return: True
        """
        planning_tournee_obj = self.env['of.planning.tournee']
        tournees_unlink = self.env['of.planning.tournee']
        for date_eval in date_list:
            employees_tournees_unlink_ids = []
            for employee_id in employee_ids:
                planning_intervention = self.search([
                    ('date_date', '<=', date_eval),
                    ('date_deadline', '>=', date_eval),
                    ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                    ('employee_ids', 'in', employee_id)], limit=1)
                if not planning_intervention:
                    # Il n'existe plus de plannings pour la tournee, on la supprime
                    employees_tournees_unlink_ids.append(employee_id)

            tournees_unlink |= planning_tournee_obj.search(
                [('date', '=', date_eval), ('employee_id', 'in', employees_tournees_unlink_ids),
                 ('is_bloque', '=', False), ('is_confirme', '=', False),
                 ('address_depart_id', '=', False), ('address_retour_id', '=', False), ('secteur_id', '=', False)])
        return tournees_unlink.unlink()

    @api.model
    def custom_get_color_map(self):
        title = ""
        v0 = {'label': u"DI à planifier", 'value': 'green'}
        # gold is easier to read than yellow on the legend with a white background
        v1 = {'label': u'Intervention(s) de la tournée', 'value': 'blue'}
        return {"title": title, "values": (v0, v1)}
