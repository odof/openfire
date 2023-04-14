# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    state = fields.Selection(selection_add=[('being_optimized', "Being optimized")])
    tournee_ids = fields.Many2many(
        comodel_name='of.planning.tournee', relation='of_planning_intervention_of_planning_tournee_rel',
        column1='intervention_id', column2='tournee_id', compute='_compute_tournee_ids', store=True,
        string="Planification")
    map_color_tour = fields.Char(compute='_compute_tour_data', string="Color")
    tour_number = fields.Char(compute='_compute_tour_data', string="Tour number")

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
            for idx, inter in enumerate(tour._get_linked_interventions(), 1):
                if not address_dict.get(inter.address_id.id):
                    address_dict[inter.address_id.id] = {inter: idx}
                else:
                    address_dict[inter.address_id.id][inter] = idx
            for rec in self:
                interventions_at_address = address_dict.get(rec.address_id.id)
                tour_number = \
                    ', '.join(map(str, interventions_at_address.values())) if interventions_at_address else False
                color = 'blue'
                rec.map_color_tour = color
                rec.tour_number = tour_number
        else:
            for rec in self:
                rec.map_color_tour = False
                rec.tour_number = False

    @api.depends('state')
    def _compute_state_int(self):
        interv_left = self.env['of.planning.intervention']
        for interv in self:
            if interv.state and interv.state == 'being_optimized':
                interv.state_int = 3
            else:
                interv_left |= interv
        super(OfPlanningIntervention, interv_left)._compute_state_int()

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
        tournees_bloquees = planning_tournees.filtered(lambda t: t.is_blocked)

        if tournees_bloquees:
            raise ValidationError(u'Un des intervenants a déjà une tournée bloquée à cette date.')

        intervention = super(OfPlanningIntervention, self).create(vals)

        tours = intervention.create_tour()

        # Updates the tour lines data
        self.update_tour_lines_data(tours)
        return intervention

    @api.multi
    def create_tour(self):
        self.ensure_one()
        # La vérif de nécessité de création de tournée est faite directement dans la fonction create_tour
        tours = self._create_tour()
        self._recompute_todo(self._fields['tournee_ids'])
        return tours

    @api.model
    def update_tour_lines_data(self, tours):
        """ Updates tour lines data for the given tours
        """
        for tour in tours:
            tour._populate_tour_lines()  # add this intervention to the tour lines if not already present
            tour._check_missing_osrm_data(force=True)

    @api.multi
    def resync_and_update_tour(self, interventions):
        """ Resyncs and update tours data.
        We should resync tours if the geodata of the interventions has changed, to update tour lines data.

        :param geodata_interventions: interventions to resync (theirs geodata has changed)
        """
        # Resyncs
        tours_to_resync = interventions.mapped('tournee_ids')
        tours_to_update = self._get_tours_to_update_on_write() - tours_to_resync
        tours_to_resync and tours_to_resync.action_compute_osrm_data(reload=True)

        # Updates
        tours_to_update and self.update_tour_lines_data(tours_to_update)

    @api.multi
    def reorder_tour(self, interventions):
        """ Reorder lines and resync/update tours data.
        We should resync tours if the geodata of the interventions has changed, to update tour lines data.

        :param geodata_interventions: interventions to resync (theirs geodata has changed)
        """
        tours = interventions.mapped('tournee_ids')
        tours and tours._reorder_tour_lines()

    @api.model
    def check_intervention_to_move(self, old_intervention_values=None):
        """ If the intervention's duration has changed, we must check if it can be moved to another tour or
        if it must be added or removed from other tours.

        For example, if the intervention's duration has been increased to 48 hours, this intervention is split in many
        interventions of X working hours, we have to had this intervention into the futurs tours.
        And in another way, if the intervention's duration has been decreased to 1 working hour, so this intervention
        should be removed from the futurs tours where it is.

        :param old_intervention_values: dict of old intervention values
        """
        if not old_intervention_values:
            return

        for intervention, old_values in old_intervention_values.iteritems():
            added_dates = list(set(intervention.get_date_tournees()))
            removed_dates = list(set(old_values) - set(intervention.get_date_tournees()))
            if added_dates:
                # Tours have been created earlier by the write method with the call to create_tour
                tours = self.env['of.planning.tournee'].sudo().search([
                    ('date', 'in', added_dates), ('employee_id', 'in', intervention.employee_ids.ids)])
                # Updates the tour lines data
                self.update_tour_lines_data(tours)
            if removed_dates:
                self.remove_from_tour({intervention: removed_dates})

    @api.model
    def remove_from_tour(self, old_intervention_values=None):
        """ Removes the intervention from its tour if the intervention's date has changed.
        """
        if not old_intervention_values:
            return

        tours_dates = old_intervention_values.values()
        interventions = self.env['of.planning.intervention'].browse()
        for intervention in old_intervention_values.keys():  # transform dict keys to recordset
            interventions |= intervention

        if not tours_dates or not interventions:
            return

        intervention_ids = interventions.ids
        existing_tour_lines = self.env['of.planning.tour.line'].sudo().search([
            ('intervention_id', 'in', intervention_ids),
            ('tour_id.date', 'in', tours_dates[0]),
            ('tour_id.date', '>=', fields.Date.today()),
        ])
        if existing_tour_lines:
            tours = existing_tour_lines.mapped('tour_id')
            existing_tour_lines.unlink()
            for tour in tours:
                tour._reset_sequence()
                tour._check_missing_osrm_data(force=True)

    @api.multi
    def write(self, vals):
        recompute_tournee_fields = self._get_recompute_tournee_fields()

        if any(
            field_name in vals for field_name in recompute_tournee_fields
        ) and self.mapped('tournee_ids').filtered('is_blocked'):
            raise ValidationError(u"La tournée d'un des intervenants est bloquée")

        interventions_to_remove = {
            intervention: intervention.get_date_tournees()
            for intervention in self._get_interventions_date_changed(vals) | self._get_cancelled_interventions(vals)
        }
        geodata_changed = self._get_interventions_geodata_updated(vals)
        hours_changed = self._get_interventions_only_hours_changed(vals)
        duration_changed = self._get_interventions_duration_changed(vals)
        force_date_changed = self._get_interventions_force_date_changed(vals)
        interventions_to_move = {
            intervention: intervention.get_date_tournees() for intervention in duration_changed | force_date_changed
        }

        res = super(OfPlanningIntervention, self).write(vals)

        if ('date' in vals or 'employee_ids' in vals) and self.mapped('tournee_ids').filtered('is_blocked'):
            raise ValidationError(u"Un des intervenants a déjà une tournée bloquée sur ce créneau")

        # avoid multiple calls to create_tour/_recompute_todo if this is not necessary
        if not self._context.get('from_tour_wizard') and any(
                field_name in vals for field_name in recompute_tournee_fields):
            for intervention in self:
                # La vérif de nécessité de création de tournée est faite directement dans la fonction _create_tour
                intervention.create_tour()

            # Updates tour lines for interventions which dates were changed or that were cancelled
            self.check_intervention_to_move(interventions_to_move)

            # Updates tour lines for interventions that have changed their date or that have been cancelled
            self.remove_from_tour(interventions_to_remove)

            # Updates tours data for interventions that have changed their hours
            self.reorder_tour(hours_changed)

            # Updates tours data or reloads it if the geodata has changed or if the intervention has been reopened
            self.resync_and_update_tour(geodata_changed)
        return res

    @api.multi
    def _get_tours_to_update_on_write(self):
        """ Helper function to get tours to update on write. It could be overridden to filter/change tours to update.
        """
        return self.filtered(lambda i: i.state != 'cancel').mapped('tournee_ids')

    @api.multi
    def unlink(self):
        tours_dates = [intervention.get_date_tournees() for intervention in self]
        flattened_tours_dates = [item for sublist in tours_dates for item in sublist]
        existing_tour_lines = self.env['of.planning.tour.line'].sudo().search([
            ('intervention_id', 'in', self.ids),
            ('tour_id.date', 'in', flattened_tours_dates)
        ])  # Tour lines are deleted in cascade so we need to get them before
        tours = existing_tour_lines and existing_tour_lines.mapped('tour_id') or self.env['of.planning.tournee']
        result = super(OfPlanningIntervention, self).unlink()
        if tours:
            # As we are deleting a tour line, we need to recompute sequences and OSRM data
            for tour in tours:
                tour._reset_sequence()
                tour._check_missing_osrm_data(force=True)
        return result

    @api.multi
    def name_get(self):
        if not self._context.get('from_tour', False):
            return super(OfPlanningIntervention, self).name_get()
        result = []
        for record in self:
            name_intervention = '%s - %s' % (record.type_id.name or record.name, record.address_id.name or 'N/A')
            result.append((record.id, name_intervention))
        return result

    # Autres

    def _get_domain_states_values_overlap(self):
        states = super(OfPlanningIntervention, self)._get_domain_states_values_overlap()
        return states + ['being_optimized']

    @api.model
    def _get_recompute_tournee_fields(self):
        return ['date', 'employee_ids', 'state', 'duree', 'address_id', 'forcer_dates']

    @api.multi
    def _get_interventions_geodata_updated(self, vals):
        """ Helper function to get interventions whose geodata has changed.

        :param vals: Values to write
        :return: interventions recordset
        """
        def _compare_geodata(i, vals):
            address_id = i.address_id and i.address_id.id or False
            if 'geo_lat' in vals and i.geo_lat != vals.get('geo_lat'):
                return True
            if 'geo_lng' in vals and i.geo_lng != vals.get('geo_lng'):
                return True
            return 'address_id' in vals and address_id != vals.get('address_id')
        return self.filtered(lambda i: _compare_geodata(i, vals))

    @api.multi
    def _get_interventions_date_changed(self, vals):
        """ Helper function to get interventions whose date has changed (to another day)

        :param vals: Values to write
        :return: interventions recordset
        """
        date_field = 'date_prompt' if 'date_prompt' in vals else 'date'
        return self.filtered(
            lambda i:
            date_field in vals and
            getattr(i, date_field) != vals.get(date_field) and
            fields.Datetime.from_string(getattr(i, date_field)).date() !=
            fields.Datetime.from_string(vals[date_field]).date())

    @api.multi
    def _get_cancelled_interventions(self, vals):
        """ Helper function to get interventions whose state has changed to 'cancelled'

        :param vals: Values to write
        :return: interventions recordset
        """
        return self.filtered(lambda i: 'state' in vals and vals.get('state') == 'cancel')

    @api.multi
    def _get_interventions_only_hours_changed(self, vals):
        """ Helper function to get interventions whose hours has changed (same date but different hours)

        :param vals: Values to write
        :return: interventions recordset
        """
        def _compare_hours(i, vals):
            if 'date' not in vals and 'date_prompt' not in vals:
                return False
            used_date = 'date_prompt' if 'date_prompt' in vals else 'date'
            date = fields.Datetime.from_string(getattr(i, used_date))
            date_new = fields.Datetime.from_string(vals[used_date])
            if date_new.date() != date.date():
                return False
            return date.hour != date_new.hour or date.minute != date_new.minute or date.second != date_new.second

        return self.filtered(lambda i: _compare_hours(i, vals))

    @api.multi
    def _get_interventions_duration_changed(self, vals):
        """ Helper function to get interventions which duration has changed

        :param vals: Values to write
        :return: interventions recordset
        """
        return self.filtered(lambda i: 'duree' in vals and i.duree != vals.get('duree'))

    @api.multi
    def _get_interventions_force_date_changed(self, vals):
        """ Helper function to get interventions which force_date has changed

        :param vals: Values to write
        :return: interventions recordset
        """
        return self.filtered(lambda i: 'forcer_dates' in vals and i.forcer_dates != vals.get('forcer_dates'))

    @api.multi
    def get_date_tournees(self):
        self.ensure_one()
        date_deb_str = self.date_date
        date_fin_str = fields.Date.to_string(fields.Date.from_string(self.date_deadline))
        res = [date_deb_str]
        # intervention sur plusieurs jours, prendre toutes les dates intermédiaires
        if date_fin_str != date_deb_str:
            date_fin_da = fields.Date.from_string(self.date_deadline)
            date_current_da = fields.Date.from_string(date_deb_str) + timedelta(days=1)
            while date_current_da <= date_fin_da:
                res.append(fields.Date.to_string(date_current_da))
                date_current_da += timedelta(days=1)
        return res

    @api.multi
    def _create_tour(self):
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
                tour = tournee_obj.search([('date', '=', date_eval), ('employee_id', '=', employee.id)], limit=1)
                address_sector = address.of_secteur_tech_id
                if not tour:
                    tour = tournee_obj.create({
                        'date': date_eval,
                        'employee_id': employee.id,
                        'sector_ids': [(6, 0, [address_sector.id])] if address_sector else False,
                        'epi_lat': address.geo_lat,
                        'epi_lon': address.geo_lng,
                        'is_blocked': False,
                        'is_confirmed': False
                    })
                elif not tour.sector_ids and address_sector:
                    tour.sector_ids = [(6, 0, [address_sector.id])]
                elif address_sector and address_sector.id not in tour.sector_ids.ids:
                    tour.sector_ids = [(4, address_sector.id)]
                res.append(tour)
        return res

    @api.multi
    def action_open_wizard_plan_intervention(self):
        self.ensure_one()
        if self.address_id and not self.address_id.geo_lat and not self.address_id.geo_lng:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))

        tour_meetup_obj = self.env['of.tournee.rdv']
        context = self._context.copy()
        default_values = tour_meetup_obj.with_context(
            active_model=self._name,
            active_ids=self.ids,
        ).default_get(tour_meetup_obj._fields.keys())
        default_values['duree'] = self.duree or self.tache_id.duree or 1.0
        default_values['service_id'] = self.service_id.id
        default_values['origin_intervention_id'] = self.id
        time_slots_new = tour_meetup_obj.new(default_values)
        # onchange to compute fields on the time slots
        time_slots_new._onchange_partner_address_id()
        time_slots_new._onchange_service()
        time_slots_new._onchange_origin_intervention_id()
        time_slots_new._onchange_tache_id()
        time_slots_new._onchange_date_recherche_fin()
        wizard_values = tour_meetup_obj._convert_to_write(time_slots_new._cache)
        time_slots_wizard = tour_meetup_obj.create(wizard_values)
        # start time slots computing
        time_slots_wizard.compute()
        form_view_id = time_slots_wizard._get_wizard_form_view_id()
        return {
            'name': _("Plan again"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.tournee.rdv',
            'views': [(form_view_id, 'form')],
            'res_id': time_slots_wizard.id,
            'target': 'new',
            'context': context
        }

    @api.model
    def custom_get_color_map(self):
        title = ""
        v0 = {'label': u"DI à planifier", 'value': 'green'}
        v1 = {'label': u'Intervention(s) de la tournée', 'value': 'blue'}
        return {"title": title, "values": (v0, v1)}
