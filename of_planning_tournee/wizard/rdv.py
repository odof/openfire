# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################


from odoo import api, models, fields
from datetime import datetime, timedelta, date
import pytz
import math
from math import cos
from odoo.addons.of_planning_tournee.models.of_planning_tournee import distance_points
from odoo.exceptions import UserError, ValidationError

RES_MODES = [
    ('tournee', u'Tournées uniquement'),
    ('hors_tournee', u'Tournées et hors tournées'),
    ('all', u'Tous créneaux, même sur tournées éloignées'),
]

def hours_to_strs(*hours):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return tuple("%02dh%02d" % (hour, round((hour % 1) * 60)) for hour in hours)

class OfTourneeRdv(models.TransientModel):
    _name = 'of.tournee.rdv'
    _description = u'Prise de RDV dans les tournées'

    @api.model
    def _default_partner(self):
        partner_id = self._context.get('active_model', '') == 'res.partner' and self._context['active_ids'][0]
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            while partner.parent_id:
                partner = partner.parent_id
            return partner
        return False

    @api.model
    def _default_service(self):
        service_obj = self.env['of.service']
        partner = self._default_partner()
        if not partner:
            return False
        services = service_obj.search([('partner_id', '=', partner.id), ('state', '=', 'progress')], limit=1)
        return services

    @api.model
    def _default_address(self):
        partner_obj = self.env['res.partner']

        partner = self._default_partner()
        if partner and partner.id != self._context['active_ids'][0]:
            # La fonction est appelée à partir d'une adresse
            return partner_obj.browse(self._context['active_ids'][0])

        address_id = partner.address_get(['delivery'])['delivery']
        if address_id:
            address = partner_obj.browse(address_id)
            if not (address.geo_lat or address.geo_lng):
                address = partner_obj.search(['|', ('partner_id', '=', partner.id), ('parent_id', '=', partner.id),
                                              '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)], limit=1)
                if not address:
                    address = partner_obj.search(['|', ('partner_id', '=', partner.id), ('parent_id', '=', partner.id)])
        return address_id

    @api.depends('planning_ids', 'planning_ids.equipe_id')
    def _get_equipe_possible(self):
        result = {}
        for res in self:
            equipes = []
            for planning in res.planning_ids:
                if not planning.equipe_id.id in equipes:
                    equipes.append(planning.equipe_id.id)
            result[res.id] = equipes
        return result

    name = fields.Char(string=u'Libellé', size=64, required=False)
    description = fields.Text(string='Description')
    tache_id = fields.Many2one('of.planning.tache', string='Prestation', required=True)
    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe")
    equipe_id_pre = fields.Many2one('of.planning.equipe', string=u'Équipe', domain="[('tache_ids','in',tache_id)]")
    duree = fields.Float(string=u'Durée', required=True, digits=(12, 5))
    planning_ids = fields.One2many('of.tournee.rdv.line', 'wizard_id', string='Proposition de RDVs')
    date_propos = fields.Datetime(string=u'RDV Début')
    date_propos_hour = fields.Float(string=u'Heude de début', digits=(12, 5))
    date_recherche = fields.Date(string='À partir du', required=True, default=lambda *a: (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'))
    partner_id = fields.Many2one('res.partner', string='Client', required=True, readonly=True, default=_default_partner)
    partner_address_id = fields.Many2one('res.partner', string="Adresse d'intervention", required=True, default=_default_address,
                                         domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    date_display = fields.Char(string='Jour du RDV', size=64, readonly=True)
    equipe_ids = fields.One2many('of.planning.equipe', compute="_get_equipe_possible", string='Équipes possibles')
    service_id = fields.Many2one('of.service', string='Service client', default=_default_service,
                                 domain="[('partner_id', '=', partner_id), ('state', '=', 'progress')]")
    date_next = fields.Date(string=u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention")
    mode = fields.Selection(RES_MODES, string="Mode de recherche", required=True, default="hors_tournee")

    @api.model
    def _get_equipe(self):
        hr_category_obj = self.env['hr.employee.category']
        equipe_ids = []
        for category in hr_category_obj.search():
            equipe_ids += category.equipe_ids._ids
        equipe_ids = list(set(equipe_ids))
        return equipe_ids


    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        service_obj = self.env['of.service']
        services = False
        if self.tache_id:
            if self.service_id:
                if self.service_id.tache_id.id == self.tache_id.id:
                    services = True
                else:
                    services = service_obj.search([('partner_id', '=', self.partner_id.id),
                                                   ('state', '=', 'progress'),
                                                   ('tache_id', '=', self.tache_id.id)], limit=1)
                    if services:
                        self.service_id = services

            if self.tache_id.duree:
                self.duree = self.tache_id.duree

            if self.equipe_id_pre not in self.tache_id.equipe_ids:
                self.equipe_id_pre = False

        if not services:
            self.service_ids = False

    @api.onchange('service_id')
    def _onchange_service(self):
        if not self.service_id:
            return

        service = self.service_id
        notes = [service.tache_id.name]
#        if service.template_id:
#            notes.append(service.template_id.name)
        if service.note:
            notes.append(service.note)

        self.description = "\n".join(notes)
        self.tache_id = service.tache_id
        self.partner_address_id = service.address_id

    # Note: Séparation en 3 fonctions car, avec une seule fonction button_calcul(self, creneau_suivant=False),
    #       Odoo place le contexte dans cette variable si elle n'est pas fournie en paramètre ...
    @api.multi
    def button_calcul_suivant(self):
        # Calcule a prochaine intervention à partir de la dernière intervention proposée
        self.compute(creneau_suivant=True)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.tournee.rdv',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }

    @api.multi
    def button_calcul(self):
        # Calcule a prochaine intervention à partir du lendemain de la date courante
        self.compute(creneau_suivant=False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.tournee.rdv',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }

    @api.multi
    def compute(self, creneau_suivant):
        u"""Calcul du prochain créneau disponible
        NOTE : Si un service est sélectionné incluant le samedi et/ou le dimanche,
               ceux-cis seront traités comme des jours normaux du point de vue des équipes
        """
        self.ensure_one()

        if 'tz' not in self._context:
            self = self.with_context(dict(self._context, tz='Europe/Paris'))
        tz = pytz.timezone(self._context['tz'])

        equipe_obj = self.env['of.planning.equipe']
        tournee_obj = self.env['of.planning.tournee']
        wizard_line_obj = self.env['of.tournee.rdv.line']
        intervention_obj = self.env['of.planning.intervention']

        address = self.partner_address_id
        service = self.service_id
        jours = [jour.id % 7 for jour in service.jour_ids] if service else range(1,6)

        # Suppression des anciens créneaux
        planning_del_ids = wizard_line_obj.search([('wizard_id', '=', self.id)])
        if planning_del_ids:
            planning_del_ids.unlink()

        # Récupération des équipes
        if not self.tache_id.equipe_ids:
            raise UserError(u"Aucune équipe ne peut réaliser cette tache.")
        if self.equipe_id_pre:
            if self.equipe_id_pre in self.tache_id.equipe_ids:
                equipes = self.equipe_id_pre
            else:
                raise UserError(u"Cette équipe n'a pas la compétence pour réaliser cette prestation.")
        else:
            equipes = self.tache_id.equipe_ids

        un_jour = timedelta(days=1)
        if creneau_suivant:
            # Récupération de la dernière date affichée
            date_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.date_propos)).date()
            # Recherche à partir du jour suivant
            date_min = fields.Date.to_string(date_date + un_jour)
            date_jour = date_date.isoweekday()
        else:
            date_min = self.date_recherche
            date_date = date_jour = False

        tournees = False
        if self.mode != 'all':
            # Recherche des tournees disponibles
            query = "SELECT id FROM of_planning_tournee "
            where_calc = "WHERE equipe_id IN %%s AND date >= '%s' AND NOT is_bloque AND NOT is_complet " % (date_min,)
            where_params = [equipes._ids]

            if service:
                where_calc += "AND EXTRACT(DOW FROM date) IN %s "
                where_params.append(tuple(jours))

            if address.geo_lat or address.geo_lng:
                geo_lat_client = address.geo_lat or 0
                geo_lng_client = address.geo_lng or 0
            else:
                # @todo: Tenter de calculer les coordonnées GPS à l'aide de l'adresse
                raise UserError(u"Le contact n'a pas de coordonnées GPS : %s" % (address.name,))

            lat = math.radians(geo_lat_client)
            lon = math.radians(geo_lng_client)
            dist_constante = 2.0*6366
            where_item = "AND asin(sqrt(pow(sin((radians(epi_lat)-(%s))/2.0),2) " \
                                           "+ cos(radians(epi_lat))*(%s)*pow(sin((radians(epi_lon)-(%s))/2.0),2))) " \
                             "* %s < distance "

            where_calc += where_item % (lat, cos(lat), lon, dist_constante)

            self._cr.execute(query + where_calc, where_params)
            tournee_ids = [row[0] for row in self._cr.fetchall()]

            # Restriction aux donnees accessibles a l'utilisateur
            tournees = tournee_obj.search([('id', 'in', tournee_ids)])

        propos = []
        while not propos:
            # Recherche jour par jour
            if self.mode == 'tournee':
                if not tournees:
                    raise UserError("Aucun créneau trouvé sur les tournées existantes")
                date = tournees[0].date
                date_date = fields.Date.from_string(date)

                equipes_dispo = []
                for tournee in tournees:
                    if tournee.date != date:
                        break
                    equipes_dispo.append(tournee.equipe_id.id)
                tournees = tournees[len(equipes_dispo):] # @todo: Vérifier ce code ([:] depuis un recordset)
                #                                          sinon: tournees = tournee_obj.browse(tournees._ids[len(equipes_dispo):])
                equipes_dispo = list(set(equipes_dispo)) # Pour le cas où il y aurait plusieurs tournées créées par erreur pour une même équipe
            else:
                if date_date:
                    date_date += un_jour
                    date_jour = (date_jour + 1) % 7
                else:
                    date_date = fields.Date.from_string(date_min)
                    date_jour = date_date.isoweekday()

                # Restriction aux jours spécifiés dans le service
                while date_jour not in jours:
                    date_jour = (date_jour + 1) % 7
                    date_date += un_jour
                date = fields.Date.to_string(date_date)

                # En mode hors tournée, interdiction de chercher dans les tournées éloignées
                # En mode tous créneaux, interdiction de chercher dans les tournées bloquées ou complètes
                query = "SELECT equipe_id FROM of_planning_tournee "
                where_calc = "WHERE equipe_id IN %%s AND date = '%s' " % (date,)
                where_params = [equipes._ids]

                if self.mode == 'hors_tournee':
                    if tournees:
                        where_calc += "AND id NOT IN %s "
                        where_params.append(tournees._ids)
                else:
                    where_calc += "AND (is_bloque OR is_complet) "

                self._cr.execute(query + where_calc, where_params)
                equipes_bloquees = [row[0] for row in self._cr.fetchall()]
                equipes_dispo = [equipe_id for equipe_id in equipes._ids if equipe_id not in equipes_bloquees]
            if not equipes_dispo:
                continue

            # Recherche de creneaux pour la date voulue et les équipes sélectionnées
            date_jour_deb = tz.localize(datetime.strptime(date+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
            date_jour_fin = tz.localize(datetime.strptime(date+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
            interventions = intervention_obj.search([('equipe_id','in',equipes_dispo),
                                                     ('date', '<=', date),
                                                     ('date_deadline', '>=', date),
                                                     ('state','in',('draft', 'confirm')),
                                                    ], order='date')

            # Récupération des interventions déjà planifiées
            equipe_intervention_dates = {equipe_id: [] for equipe_id in equipes_dispo}
            for intervention in interventions:
                intervention_dates = [intervention]
                for intervention_date in (intervention.date, intervention.date_deadline):
                    # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                    date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention_date))

                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    date_local = max(date_local, date_jour_deb)
                    date_local = min(date_local, date_jour_fin)
                    date_local_flo = round(date_local.hour +
                                           date_local.minute / 60.0 +
                                           date_local.second / 3600.0, 5)
                    intervention_dates.append(date_local_flo)

                equipe_intervention_dates[intervention.equipe_id.id].append(intervention_dates)

            # @todo: Gestion des employés dans plusieurs équipes
            for equipe in equipe_obj.browse(equipes_dispo):
                intervention_dates = equipe_intervention_dates[equipe.id]

                deb = equipe.hor_md
                fin = equipe.hor_mf
                ad = equipe.hor_ad
                creneaux = []

                for intervention, intervention_deb, intervention_fin in intervention_dates + [(False, 24, 24)]:
                    if deb < intervention_deb and deb < fin:
                        # Un trou dans le planning, suffisant pour un créneau?

                        if deb < ad and intervention_deb >= ad:
                            # On passe du matin à l'après-midi
                            # On vérifie la durée cumulée de la matinée et de l'après-midi car une intervention peut
                            # commencer avant la pause repas
                            intervention_deb = min(intervention_deb, equipe.hor_af)
                            duree = equipe.hor_mf - deb + intervention_deb - ad
                            if duree >= self.duree:
                                creneaux.append((deb, fin, equipe))
                                creneaux.append((ad, intervention_deb, equipe))
                            fin = equipe.hor_af
                        else:
                            duree = min(intervention_deb, fin) - deb
                            if duree >= self.duree:
                                creneaux.append((deb, deb+duree, equipe))

                    if intervention_fin >= fin and fin <= ad:
                        deb = max(intervention_fin, ad)
                        fin = equipe.hor_af
                    elif intervention_fin > deb:
                        deb = intervention_fin

                if not creneaux:
                    # Aucun creneau libre pour cette équipe
                    continue

                propos = min(propos, creneaux[0]) or creneaux[0]

                for intervention_deb, intervention_fin, equipe in creneaux:
                    description = "%s-%s" % tuple(hours_to_strs(intervention_deb, intervention_fin))

                    wizard_line_obj.create({
                        'date_flo': intervention_deb,
                        'date_flo_deadline': intervention_fin,
                        'description': description,
#                            'jour_res_id': plan[3],
                        'wizard_id': self.id,
                        'equipe_id': equipe.id,
                        'intervention_id': False,
                    })
                for intervention, intervention_deb, intervention_fin in intervention_dates:
                    description = "%s-%s" % tuple(hours_to_strs(intervention_deb, intervention_fin))

                    wizard_line_obj.create({
                        'date_flo': intervention_deb,
                        'date_flo_deadline': intervention_fin,
                        'description': description,
#                            'jour_res_id': plan[3],
                        'wizard_id': self.id,
                        'equipe_id': intervention.equipe_id.id,
                        'intervention_id': intervention.id,
                    })

        # libelle de RDV
        address = self.partner_address_id
        name = address.name or (address.parent_id and address.parent_id.name) or ''
        name += address.zip and (" " + address.zip) or ""
        name += address.city and (" " + address.city) or ""

        datetime_propos = datetime.combine(date_date, datetime.min.time()) + timedelta(hours=propos[0])
        datetime_propos = tz.localize(datetime_propos, is_dst=None).astimezone(pytz.utc)

        vals = {
            'date_display'    : date_date.strftime('%A %d %B %Y'),
            'name'            : name,
            'equipe_id'       : propos[2].id,
            'date_propos'     : datetime_propos,
            'date_propos_hour': propos[0],
        }

        if self.service_id:
            vals['date_next'] = self.service_id.get_next_date(date_date.strftime('%Y-%m-%d'))
        else:
            vals['date_next'] = "%s-%02i-01" % (date_date.year + 1, date_date.month)
        self.write(vals)

    @api.multi
    def _get_service_data(self, mois):
        return {
            'partner_id': self.partner_id.id,
            'partner_address_id': self.partner_address_id.id,
            'tache_id': self.tache_id.id,
            'mois_ids': [(4, mois)],
            'date_next': self.date_next,
            'note': self.description or '',
        }

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        if 'tz' not in self._context:
            self = self.with_context(dict(self._context, tz='Europe/Paris'))
        tz = pytz.timezone(self._context['tz'])

        intervention_obj = self.env['of.planning.intervention']
        service_obj = self.env['of.service']

        # verifier que la date de début est dans les créneaux
        equipe = self.equipe_id
        date_display = self.date_display
        date_propos_hour = self.date_propos_hour
        date_date = datetime.strptime(date_display.encode('utf8'), "%A %d %B %Y")

        date_propos_local_datetime_sanszone = date_date + timedelta(minutes=round(date_propos_hour*60))
        local_dt = tz.localize(date_propos_local_datetime_sanszone, is_dst=None)
        date_propos_utc = local_dt.astimezone(pytz.utc)
        date_propos = date_propos_utc.strftime('%Y-%m-%d %H:%M:%S')

        date_propos_deadline_local_datetime_sanszone = date_propos_local_datetime_sanszone + timedelta(hours=self.duree)
        for planning in self.planning_ids:
            if (not planning.intervention_id) and (planning.equipe_id.id == equipe.id):
                debut = datetime.combine(date_date, datetime.min.time()) + timedelta(hours=planning.date_flo)
                fin = datetime.combine(date_date, datetime.min.time()) + timedelta(hours=planning.date_flo_deadline)
                if (date_propos_local_datetime_sanszone >= debut) and (date_propos_local_datetime_sanszone <= fin) and \
                    (date_propos_deadline_local_datetime_sanszone >= debut) and (date_propos_deadline_local_datetime_sanszone <= fin):
                    break
        else:
            raise UserError(u"Vérifier la date de RDV et l'équipe technique")

        if (not equipe.hor_md) or (not equipe.hor_mf) or (not equipe.hor_ad) or (not equipe.hor_af):
            raise UserError("Il faut configurer l'horaire de travail de toutes les équipes.")

        values = {
            'hor_md': equipe.hor_md,
            'hor_mf': equipe.hor_mf,
            'hor_ad': equipe.hor_ad,
            'hor_af': equipe.hor_af,
            'partner_id': self.partner_id.id,
            'partner_id': self.partner_address_id.id,
            'tache_id': self.tache_id.id,
            'equipe_id': self.equipe_id.id,
            'date': date_propos,
            'duree': self.duree,
            'user_id': self._uid,
            'company_id': self.partner_address_id.company_id and self.partner_address_id.company_id.id,
            'name': self.name,
            'description': self.description or '',
            'state': 'confirm',
            'verif_dispo': True,
        }

        # Si rdv RES pris depuis un SAV, on le lie au SAV
        if self._context.get('active_model') == 'crm.helpdesk':
            values['sav_id'] = self._context.get('active_id',False)

        intervention_obj.create(values)

        # Creation/mise à jour du service
        if self.date_next:
            if self.service_id:
                self.service_id.write({'date_next': self.date_next})
            else:
                service_obj.create(self._get_service_data(self, date_propos_utc.month))
        return {'type': 'ir.actions.act_window_close'}


class OfTourneeRdvLine(models.TransientModel):
    _name = 'of.tournee.rdv.line'
    _description = 'Propositions des RDVs'

    @api.depends()
    def _calc_distances(self):
        jours_res = {}
        for line in self:
            jours_res.setdefault(line.wizard_id, {}).setdefault(line.equipe_id, []).append(line)

        for wizard, equipes in jours_res.iteritems():
            partner_address = wizard.partner_address_id
            for equipe, lines in equipes.iteritems():
                lines_libres = []
                last_gps = (equipe.address_id.geo_lat, equipe.address_id.geo_lng)
                next_gps = False
                lines.sort(key=lambda p: p.date_flo)
                for line in lines+[False]:
                    if line is False:
                        address = equipe.address_id
                        next_gps = (address.geo_lat, address.geo_lng)
                    elif line.intervention_id:
                        address = line.intervention_id.address_id
                        next_gps = (address.geo_lat, address.geo_lng)

                        line.distance = ''
                        line.dist_prec = ''
                        line.dist_suiv = ''
                    else:
                        lines_libres.append(line)

                    if next_gps:
                        for line in lines_libres:
                            erreur = False
                            dist_tot = 0
                            vals = []
                            for gps in (last_gps, next_gps):
                                if gps[0]:
                                    dist = distance_points(gps[0], gps[1], partner_address.geo_lat, partner_address.geo_lng)
                                    dist_tot += dist
                                    vals.append("%0.2f" % dist)
                                else:
                                    vals.append('?')
                                    erreur = '?'

                            line.distance = erreur or "%0.2f" % dist_tot
                            line.dist_prec = vals[0]
                            line.dist_suiv = vals[1]
                        lines_libres = []
                        last_gps = next_gps
                        next_gps = False

    date_flo = fields.Float(string='Date', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    description = fields.Char(string='RDV', size=128)
#    tournee_id = fields.Many2one('of.planning.tournee', string="Jour RES")
    wizard_id = fields.Many2one('of.tournee.rdv', string="RDV", required=True, ondelete='cascade')
    equipe_id = fields.Many2one('of.planning.equipe', string='Equipe')
    intervention_id = fields.Many2one('of.planning.intervention', string="Planning")

    distance = fields.Char(compute="_calc_distances", string='Dist.tot.')
    dist_prec = fields.Char(compute="_calc_distances", string='Dist.Prec.')
    dist_suiv = fields.Char(compute="_calc_distances", string='Dist.Suiv')

    _order = "date_flo"
