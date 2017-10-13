# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta
import math
from math import cos
import pytz
from pytz import timezone
from odoo.addons.of_planning_tournee.models.of_planning_tournee import distance_points
from odoo.addons.of_planning_tournee.wizard.rdv import hours_to_strs
from odoo.exceptions import UserError
from __builtin__ import True

class OfTourneePlanification(models.TransientModel):
    _name = 'of.tournee.planification'
    _description = 'Planification de RDV'

    @api.depends('tournee_id', 'tournee_id.date')
    def _get_date_display(self):
        for planif in self:
            date_tournee_datetime = fields.Date.from_string(planif.tournee_id.date)
            planif.date_display = date_tournee_datetime.strftime('%A %d %B %Y')

    @api.model
    def _get_partner_ids(self, tournee):
        partner_obj = self.env['res.partner']
        service_obj = self.env['of.service']

        taches = tournee.equipe_id.tache_ids

        date_tournee = tournee.date
        date_tournee_datetime = fields.Date.from_string(date_tournee)
        date_jour = date_tournee_datetime.isoweekday()

        services = service_obj.search([
            ('tache_id', 'in', taches._ids),
            ('date_next', '<=', date_tournee),
            ('jour_ids', 'in', [date_jour]),
            ('partner_id', '!=', False),
            ('state', '=', 'progress')
        ])

        if not services:
            return []

        partner_services = {}
        for service in services:
            partner_services.setdefault(service.partner_id.id, []).append(service)

        # Recherche des partenaires dans la zone géographique
        # Nous utilisons une requete sql dans un souci de performance
        query = "SELECT DISTINCT id\n" \
                "FROM res_partner\n" \
                "WHERE id IN %%s\n" \
                "AND asin(sqrt(pow(sin((radians(geo_lat)-(%s))/2.0),2) + cos(radians(geo_lat))*(%s)*pow(sin((radians(geo_lng)-(%s))/2.0),2))) < %s "

        lat = math.radians(tournee.epi_lat)
        lon = math.radians(tournee.epi_lon)
        dist = tournee.distance / (2.0 * 6366)
        self._cr.execute(query % (lat, cos(lat), lon, dist), (tuple(partner_services.keys()),))

        partner_ids = [row[0] for row in self._cr.fetchall()]
        partners = []

        for partner in partner_obj.browse(partner_ids):
            for service in partner_services[partner.id]:
                service_tache_duree = service.tache_id.duree
                phone = partner.phone or ''
                phone += partner.mobile and ((phone and ' || ' or '') + partner.mobile) or ''
                partners.append((0, 0, {
                    'service_id': service.id,
                    'duree': service_tache_duree or 0.0,
                    'tache_possible': taches._ids,
                }))
        return partners

    @api.model
    def _get_planning_ids(self, tournee):
        intervention_obj = self.env['of.planning.intervention']
        service_obj = self.env['of.service']

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        equipe = tournee.equipe_id
        date_intervention = tournee.date

        # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
        #   (pour les interventions étalées sur plusieurs jours)
        tz = pytz.timezone(self._context['tz'])
        date_min = tz.localize(datetime.strptime(date_intervention+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
        date_max = tz.localize(datetime.strptime(date_intervention+" 23:59:00", "%Y-%m-%d %H:%M:%S"))

        plannings = []
        if equipe.hor_md and equipe.hor_mf and equipe.hor_ad and equipe.hor_af:
            equipe_hor_md = equipe.hor_md
            equipe_hor_mf = equipe.hor_mf
            equipe_hor_ad = equipe.hor_ad
            equipe_hor_af = equipe.hor_af

            # Récupération des RDVs déjà créés
            interventions = intervention_obj.search([
                ('date_deadline', '>=', date_intervention),
                ('date', '<=', date_intervention),
                ('equipe_id', '=', equipe.id),
                ('state', 'in', ('draft', 'confirm', 'done'))], order='date, date_deadline DESC')
            hor_list = []   # date_flo, date_deadline_flo, libelle, tache_id, duree, partner_id

            prev_date_deadline = False
            for intervention in interventions:
                if prev_date_deadline and prev_date_deadline >= intervention.date_deadline:
                    # Ce rdv est inclus dans un autre
                    continue
                prev_date_deadline = intervention.date_deadline
                data = [intervention]
                for intervention_date in (intervention.date, intervention.date_deadline):
                    date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention_date))
                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    date_local = max(date_local, date_min)
                    date_local = min(date_local, date_max)

                    date_local_flo = round(date_local.hour +
                                           date_local.minute / 60.0 +
                                           date_local.second / 3600.0, 5)
                    data.append(date_local_flo)
                hor_list.append(data)

            equipe_hor_list = []   # date_debut, date_fin
            if equipe_hor_mf == equipe_hor_ad:
                equipe_hor_list.append([equipe_hor_md, equipe_hor_af])
            else:
                equipe_hor_list.append([equipe_hor_md, equipe_hor_mf])
                equipe_hor_list.append([equipe_hor_ad, equipe_hor_af])

            debut_add = 0.0
            for eh in equipe_hor_list:
                debut_add = max(eh[0], debut_add)
                if debut_add >= eh[1]:
                    continue
                debut_add_str, fini_add_str = hours_to_strs(debut_add, eh[1])

                while hor_list:
                    if hor_list[0][1] >= eh[1]:
                        break
                    intervention, date_flo, date_flo_deadline = hor_list.pop(0)
                    if debut_add < date_flo:
                        debut_str, fin_str = hours_to_strs(debut_add, date_flo)
                        plannings.append((0, 0, {
                            'name': "%s-%s" % (debut_str, fin_str),
                            'is_occupe': False,
                            'is_planifie': False,
                            'date_flo': debut_add,
                            'date_flo_deadline': date_flo,
                        }))

                    service = service_obj.search([
                        ('tache_id', '=', intervention.tache_id.id),
                        ('address_id', '=', intervention.address_id.id),
                        ('state', '=', 'progress')
                    ])

                    plannings.append((0, 0, {
                        'name': intervention.name,
                        'is_occupe': True,
                        'is_planifie': True,
                        'date_flo': date_flo,
                        'date_flo_deadline': date_flo_deadline,
                        'tache_id': intervention.tache_id.id,
                        'duree': intervention.duree,
                        'partner_id': intervention.partner_id and intervention.partner_id.id,
                        'partner_address_id': intervention.address_id and intervention.address_id.id,
                        'service_id': service and service[0].id or False,
                    }))
                    debut_add = date_flo_deadline
                    debut_add_str = hours_to_strs(date_flo_deadline)[0]

                if eh[1] > debut_add:
                    plannings.append((0, 0, {
                        'name': debut_add_str + '-' + fini_add_str,
                        'is_occupe': False,
                        'is_planifie': False,
                        'date_flo': debut_add,
                        'date_flo_deadline': eh[1],
                    }))

        return plannings

    tournee_id = fields.Many2one('of.planning.tournee', string=u'Tournée', required=True, ondelete='cascade')

    plan_partner_ids = fields.One2many('of.tournee.planification.partner', 'wizard_id', string='Clients')
    plan_planning_ids = fields.One2many('of.tournee.planification.planning', 'wizard_id', string='RDV')
    date_display = fields.Char(compute='_get_date_display', string='Jour')
    distance_add = fields.Float(string=u'Éloignement maximum (km)', digits=(12, 3))

    zip_id = fields.Many2one(related='tournee_id.zip_id')
    distance = fields.Float(related='tournee_id.distance')
    equipe_id = fields.Many2one(related='tournee_id.equipe_id')

    @api.multi
    def _get_show_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.tournee.planification',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }

    @api.multi
    def _get_refresh_action(self):
        return self._get_show_action()

    @api.multi
    def button_planifier(self, plan_partner_ids=False):
        """
        Planifie des rendez-vous en deplacant des clients de plan_partner_ids vers plan_planning_ids
        @param plan_partner_ids: Si defini, seuls les partenaires correspondants pourront etre deplaces
        """
        self.ensure_one()
        partner_obj = self.env['res.partner']

        equipe = self.equipe_id
        plan_partners = []
        date_planifi_list = []   # debut, fin, line_id

        if not self.plan_planning_ids:
            raise UserError(u"Vous devez configurer les horaires de travail de l'équipe")

        for line in self.plan_partner_ids:
            if (plan_partner_ids is not False) and (line.id not in plan_partner_ids):
                continue
            rp = line.partner_address_id
            if not rp:
                raise UserError(u"Vous n'avez pas configuré le GPS du client %s" % (line.partner_id.name,))
            if rp.geo_lat or rp.geo_lng:
                plan_partners.append(line)
                if line.date_flo and line.date_flo_deadline and (plan_partner_ids is not False):
                    date_planifi_list.append([line.date_flo, line.date_flo_deadline, line.id])
        if not (equipe.geo_lat or equipe.geo_lng):
            raise UserError(u"Vous devez configurer l'adresse de l'équipe")
        if not plan_partners:
            return

        plan_plans = []
        new_plan_partners = []

        new_planning_list = self.plan_planning_ids[:]
        if date_planifi_list:
            # Partenaires dans la liste plan_partner_ids (plan_partner_ids is not False)
            # Et dont un horaire a été spécifié. Leur placement est donc prioritaire sur les calculs de distances
            date_planifi_list.sort()
            for planning in self.plan_planning_ids:
                if planning.address_id or planning.is_planifie:
                    # Déjà planifié
                    continue

                # Créneau disponible
                plan_plans.append((2, planning.id))
                new_planning_list.remove(planning)
                hor_fin = planning.date_flo
                while 1:
                    if hor_fin >= planning.date_flo_deadline:
                        break
                    if not date_planifi_list:
                        new_planning_list.append(self.make_planning(hor_fin, planning.date_flo_deadline, False))
                        break

                    # tester si il y a les dates planifies dans ce creneau
                    date_planifi_debut, date_planifi_fin, date_planifi_line_id = date_planifi_list[0]
                    if date_planifi_debut < planning.date_flo_deadline:
                        if date_planifi_debut != hor_fin:
                            # L'heure de debut de la tache ne correspond pas au début du creneau : on crée un créneau vide avant la tache
                            new_planning_list.append(self.make_planning(hor_fin, date_planifi_debut, False))
                        # Récupération de la ligne du partenaire
                        index = 0
                        for plan_partner in plan_partners:
                            if plan_partner.id == date_planifi_line_id:
                                break
                            index += 1
                        # Creation de la ligne de planning
                        address = plan_partner.partner_address_id
                        libelle = address.name
                        for field in ['zip', 'city']:
                            if address[field]:
                                libelle += " "+address[field]
                        new_planning_list.append(self.make_planning(date_planifi_debut, date_planifi_fin, True,
                                                                    service=plan_partner.service_id, libelle=libelle))
                        hor_fin = date_planifi_fin
                        del plan_partners[index]
                        del date_planifi_list[0]
                        new_plan_partners.append((3, plan_partner.id))
                    else:
                        # La tache est ulterieure au creneau : on comble l'horaire avec un nouveau creneau vide
                        new_planning_list.append(self.make_planning(hor_fin, planning.date_flo_deadline, False))
                        break

        last_geo_lat = 0
        last_geo_lng = 0
        for new_planning in new_planning_list:
            # Placement de taches sur les creneaux disponibles en fonction de la distance a la tache precedente.
            is_planifi = False
            # Test de creneau deja attribue
            if isinstance(new_planning, (list, tuple)):
                if new_planning[2]['is_occupe']:
                    is_planifi = True
                    plan_plans.append(new_planning)
                    address = partner_obj.browse(new_planning[2]['partner_address_id'])
                    last_geo_lat = address.geo_lat or 0
                    last_geo_lng = address.geo_lng or 0
            else:
                if new_planning.partner_address_id or new_planning.is_planifie:
                    is_planifi = True
                    if new_planning.partner_address_id.geo_lat or new_planning.partner_address_id.geo_lng:
                        last_geo_lat = new_planning.partner_address_id.geo_lat
                        last_geo_lng = new_planning.partner_address_id.geo_lng

            if is_planifi:
                continue
            if not (last_geo_lat or last_geo_lng):
                last_geo_lat = equipe.geo_lat
                last_geo_lng = equipe.geo_lng

            # Creneau disponible
            if isinstance(new_planning, (list, tuple)):
                new_hor_fin = new_planning[2]['date_flo']
                planning_deadline = new_planning[2]['date_flo_deadline']
            else:
                plan_plans.append((3, new_planning.id))
                new_hor_fin = new_planning.date_flo
                planning_deadline = new_planning.date_flo_deadline

            while 1:
                if (new_hor_fin >= planning_deadline):
                    break
                if not plan_partners:
                    plan_plans.append(self.make_planning(new_hor_fin, planning_deadline, False))
                    break
                min_distance = False

                i = index = -1
                for plan_partner in plan_partners:
                    i += 1
                    if new_hor_fin + plan_partner.duree > planning_deadline:
                        continue
                    address = plan_partner.partner_address_id
                    distance = distance_points(last_geo_lat, last_geo_lng, address.geo_lat, address.geo_lng)
                    if min_distance is False or distance < min_distance:
                        min_distance = distance
                        index = i

                if index == -1:
                    # Pas de client disponible pour le creneau restant (ou creneau vide)
                    plan_plans.append(self.make_planning(new_hor_fin, planning_deadline, False))
                    break

                # Creation de la ligne de planning
                plan_partner = plan_partners.pop(index)
                address = plan_partner.partner_address_id
                libelle = address.name
                for field in ['zip', 'city']:
                    if address[field]:
                        libelle += " "+address[field]

                plan_plans.append(self.make_planning(new_hor_fin, (new_hor_fin + plan_partner.duree), True,
                                                     service=plan_partner.service_id, libelle=libelle))
                new_hor_fin += plan_partner.duree
                last_geo_lat = address.geo_lat
                last_geo_lng = address.geo_lng
                new_plan_partners.append((3, plan_partner.id))

        if plan_plans:
            self.write({'plan_planning_ids': plan_plans, 'plan_partner_ids': new_plan_partners})
        return self._get_refresh_action()

    @api.multi
    def creneau(self, creneau_avant, creneau_apres, start, end):
        modif_planning = []
        if creneau_apres:
            end = creneau_apres.date_flo_deadline
            modif_planning.append((3, creneau_apres.id))
        if creneau_avant:
            start = creneau_avant.date_flo
            modif_planning.append((3, creneau_avant.id))
        add_creneau = self.make_planning(start, end, False)
        modif_planning.append(add_creneau)
        return modif_planning

    @api.multi
    def make_planning(self, hor_debut, hor_fin, is_occupe, service=False, libelle=False):
        if not libelle:
            libelle = "%s-%s" % hours_to_strs(hor_debut, hor_fin)

        data = {
            'date_flo': hor_debut,
            'date_flo_deadline': hor_fin,
            'name': libelle,
            'is_occupe': is_occupe,
            'is_planifie': False,
        }
        if service:
            data.update({
                'service_id': service.id,
                'tache_id': service.tache_id.id,
                'partner_address_id': service.address_id.id,
                'duree': service.tache_id.duree,
                'date_next': service.get_next_date(self.tournee_id.date),
            })
        return (0, 0, data)

    @api.multi
    def button_plan_auto(self):
        return self.button_planifier(False)

    @api.multi
    def button_confirm(self):
        for plan in self:
            plan.plan_planning_ids.button_confirm()
        return self._get_refresh_action()

class OfTourneePlanificationPartner(models.TransientModel):
    _name = 'of.tournee.planification.partner'
    _description = 'Partenaire de Planification de RDV'

    @api.depends('service_id')
    def _get_phone(self):
        for plan_partner in self:
            address = plan_partner.service_id.address_id
            # Champs affichés pour le numéro de téléphone, si renseignés
            phone = (address.phone, address.mobile)
            plan_partner.phone = ' || '.join([p for p in phone if p])

    wizard_id = fields.Many2one('of.tournee.planification', string="Planification", required=True, ondelete='cascade')
    service_id = fields.Many2one('of.service', string="Service", required=True, ondelete='cascade')

    partner_id = fields.Many2one(related='service_id.partner_id')
    partner_address_id = fields.Many2one(related='service_id.address_id')
    tache_id = fields.Many2one(related='service_id.tache_id')
    phone = fields.Char(compute='_get_phone')

    tache_possible = fields.Many2many('of.planning.tache', related="wizard_id.tournee_id.equipe_id.tache_ids", string="Intervention Possible")

    duree = fields.Float(string=u'Durée', required=True, digits=(12, 5))
    distance = fields.Float(string='Dist.tot.', digits=(12, 3))
    dist_prec = fields.Float(string='Prec.', digits=(12, 3))
    dist_suiv = fields.Float(string='Suiv', digits=(12, 3))
    date_flo = fields.Float(string='RDV', digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', digits=(12, 5))
    is_changed = fields.Boolean(string=u'Modifié')   # seulement quand on modifie la duree ou la date debut, c'est egale True

    @api.multi
    def button_add_plan(self):
        return self.wizard_id.button_planifier(self._ids)

    @api.onchange('date_flo', 'duree')
    def _onchange_tache_duree(self):
        self.is_changed = True
        if self.duree and self.date_flo:
            self.date_flo_deadline = round(self.date_flo + self.duree, 5)

class OfTourneePlanificationPlanning(models.TransientModel):
    _name = 'of.tournee.planification.planning'
    _description = u'Résultat de Planification de RDV'

    name = fields.Char(u'Libellé', size=128, required=True)
    wizard_id = fields.Many2one('of.tournee.planification', string="Planification", ondelete='cascade')
    service_id = fields.Many2one('of.service', string="Service", ondelete='cascade')

    tache_id = fields.Many2one('of.planning.tache', string='Intervention', ondelete='cascade')
#    partner_id = fields.Many2one('res.partner', string='Client')
    partner_address_id = fields.Many2one('res.partner', string='Adresse', ondelete='cascade')

    date_flo = fields.Float(string='RDV', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    duree = fields.Float(string=u'Durée', digits=(12, 5))
    is_occupe = fields.Boolean(string=u'Occupé')
    is_planifie = fields.Boolean(string=u'Déjà Planifié')
    service_id = fields.Many2one('of.service', string="Service", readonly=True)
    date_next = fields.Date(string=u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention")

    _order = "date_flo"

    @api.multi
    def button_del_plan(self):
        for planning in self:
            if planning.is_planifie:
                # Ne devrait pas arriver car le bouton suppression des plannings confirmés est masque
                raise UserError(u'Les RDVs déjà planifiés se suppriment depuis le planning de pose')
            if not planning.partner_address_id:
                # Ne devrait pas arriver car le bouton suppression des creneaux est masqué
                raise UserError(u'Vous ne pouvez pas supprimer les créneaux')

            # Ajouter dans la table partenaire
            address = planning.partner_address_id
            phone = [p for p in (address.phone, address.mobile) if p]
            phone = ' || '.join(phone)
            add_partner = [(0, 0, {
                'service_id': planning.service_id.id,
                'duree': planning.duree or 0.0,
            })]
            # Supprimer le planning
            modif_planning = [(3, planning.id)]

            # Ajouter créneau et vérifier si il y a les créneaux à fusionner
            wizard = planning.wizard_id

            creneau_avant = self.search([('date_flo', '=', planning.date_flo_deadline), ('wizard_id', '=', wizard.id), ('is_occupe', '=', False)], limit=1)
            creneau_apres = self.search([('date_flo_deadline', '=', planning.date_flo), ('wizard_id', '=', wizard.id), ('is_occupe', '=', False)], limit=1)
            cre_res = wizard.creneau(creneau_avant, creneau_apres, planning.date_flo, planning.date_flo_deadline)
            modif_planning = modif_planning + cre_res

            wizard.write({'plan_partner_ids': add_partner, 'plan_planning_ids': modif_planning})
        return wizard._get_refresh_action()

    @api.multi
    def button_trier(self):
        self.ensure_one()

        wizard = self.wizard_id
        if self.is_occupe:
            address = self.partner_address_id
            lat = address.geo_lat
            lon = address.geo_lng
            for partner in wizard.plan_partner_ids:
                partner_lat = partner.partner_address_id.geo_lat
                partner_lon = partner.partner_address_id.geo_lng
                if partner_lat or partner_lon:
                    partner.write({'dist_prec': 0.0, 'dist_suiv': 0.0, 'distance': distance_points(lat, lon, partner_lat, partner_lon)})
                else:
                    raise UserError(u"Vous n'avez pas configuré le GPS du client %s" % (partner.partner_id.name or '',))
        else:
            # On a cliqué sur une case sans rendez-vous, on va donc chercher en fonction des rendez-vous qui l'encadrent.
            # Si il n'y a pas de rendez-vous avant ou apres, on se basera sur l'adresse du poseur
            p_prec = p_suiv = wizard.equipe_id
            found = False
            for planning in wizard.plan_planning_ids:
                if planning == self:
                    found = True
                elif found:
                    if planning.partner_address_id:
                        p_suiv = planning.partner_address_id
                        break
                else:
                    if planning.partner_address_id:
                        p_prec = planning.partner_address_id

            p_lat = p_prec.geo_lat
            p_lon = p_prec.geo_lng
            if p_suiv:
                s_lat = p_suiv.geo_lat
                s_lon = p_suiv.geo_lng

            for partner in wizard.plan_partner_ids:
                partner_lat = partner.partner_address_id.geo_lat
                partner_lon = partner.partner_address_id.geo_lng

                if partner_lat or partner_lon:
                    dist_prec = distance_points(p_lat, p_lon, partner_lat, partner_lon)
                    dist_suiv = p_suiv and distance_points(s_lat, s_lon, partner_lat, partner_lon) or 0.0
                    partner.write({'dist_prec': dist_prec, 'dist_suiv': dist_suiv, 'distance': dist_prec + dist_suiv})
                else:
                    raise UserError(u"Vous n'avez pas configuré le GPS du client %s" % (partner.partner_id.name or ''))
        return wizard._get_refresh_action()

    @api.multi
    def button_confirm(self):
        intervention_obj = self.env['of.planning.intervention']

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        for planning in self:
            if planning.is_planifie:
                continue
            if not planning.is_occupe:
                continue

            wizard = planning.wizard_id
            equipe = wizard.equipe_id
            date_date = fields.Datetime.from_string(wizard.tournee_id.date)
            local_tz = timezone(self._context['tz'])
            utc = timezone('UTC')

            date_datetime = date_date + timedelta(hours=planning.date_flo)
            date_datetime_local = local_tz.localize(date_datetime)
            date_datetime_sanszone = date_datetime_local.astimezone(utc)
            date_str = fields.Datetime.to_string(date_datetime_sanszone)

            service = planning.service_id
            address = service.address_id
            # Champs affichés dans la description de la pose
            description = (
                service.tache_id.name,
                # service.template_id and service.template_id.name,
                service.note,
            )
            description = "\n".join([s for s in description if s])

            values = {
                'hor_md'     : equipe.hor_md,
                'hor_mf'     : equipe.hor_mf,
                'hor_ad'     : equipe.hor_ad,
                'hor_af'     : equipe.hor_af,
                'partner_id' : service.partner_id.id,
                'address_id' : address.id,
                'tache_id'   : service.tache_id.id,
                'equipe_id'  : equipe.id,
                'date'       : date_str,
                'duree'      : planning.duree,
                'user_id'    : self._uid,
                'company_id' : service.partner_id.company_id.id,
                'name'       : planning.name,
                'state'      : 'draft',
                'description': description,
                'verif_dispo': True,
            }
            intervention_obj.create(values)

            # Mise à jour de la date minimale de prochaine intervention dans le service
            if planning.date_next:
                planning.service_id.write({'date_next': planning.date_next})

            planning.write({'is_planifie': True})
        return wizard._get_refresh_action()
