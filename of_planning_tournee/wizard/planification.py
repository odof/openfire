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
            ('partner_id','!=', False),
            ('state', '=', 'progress')
        ])

        if not services:
            return []

        partner_services = {}
        for service in services:
            partner_services.setdefault(service.partner_id.id,[]).append(service)

        # Recherche des partenaires dans la zone géographique
        # Nous utilisons une requete sql dans un souci de performance
        query = "SELECT DISTINCT id\n" \
                "FROM res_partner\n" \
                "WHERE id IN %%s\n" \
                "AND asin(sqrt(pow(sin((radians(geo_lat)-(%s))/2.0),2) + cos(radians(geo_lat))*(%s)*pow(sin((radians(geo_lng)-(%s))/2.0),2))) < %s "

        
        lat = math.radians(tournee.epi_lat)
        lon = math.radians(tournee.epi_lon)
        dist= tournee.distance / (2.0*6366)
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
                        ('address_id','=', intervention.address_id.id),
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

    tournee_id = fields.Many2one('of.planning.tournee', string=u'Tournée', required=True)

    plan_partner_ids = fields.One2many('of.tournee.planification.partner', 'wizard_id', string='Clients')
    plan_planning_ids = fields.One2many('of.tournee.planification.planning', 'wizard_id', string='RDV')
    date_display = fields.Char(compute='_get_date_display', string='Jour')
    distance_add = fields.Float(string=u'Éloignement maximum (km)', digits=(12,3))

    zip_id = fields.Many2one(related='tournee_id.zip_id')
    distance = fields.Float(related='tournee_id.distance')
    equipe_id = fields.Many2one(related='tournee_id.equipe_id')

#     _columns = {
#         'date'                  : fields.date('Date'),
#         'date_jour'             : fields.char('Jour', size=24),
#         'equipe_id'             : fields.many2one('of.planning.equipe', 'Equipe'),
#         'zip'                   : fields.char('Code Postal', size=24),
#         'city'                  : fields.char('Ville', size=128),
#         'distance'              : fields.float('Eloignement (km)', digits=(12,3)),
#         'plan_partner_ids'      : fields.one2many('of.res.planification.partner', 'wizard_plan_id', 'Clients'),
#         'plan_partner_ids_dis1' : fields.related('plan_partner_ids', type='one2many', relation='of.res.planification.partner', string='Clients'),
#         'plan_planning_ids'     : fields.one2many('of.res.planification.planning', 'wizard_plan_id', 'RDV'),
#         'plan_planning_ids_dis1': fields.related('plan_planning_ids', type='one2many', relation='of.res.planification.planning', string='RDV', store=False),
#         'len_plannings'         : fields.function(_get_len_plannings, method=True, type='integer'),
#         'date_display'          : fields.char('RES Jour', size=64),
#         'distance_add'          : fields.float('Eloignement maximum (km)', digits=(12,3)),
#         'epi_lat'               : fields.float('Epicentre Lat', digits=(12, 12), required=True),
#         'epi_lon'               : fields.float('Epicentre Lon', digits=(12, 12), required=True),
#     }

#     _defaults = {
#         'date_display': _get_date_display,
#         'plan_partner_ids': _get_partner_ids,
#         'plan_planning_ids': _get_planning_ids,
#     }

#     @api.model
#     def create(self, vals):
#         tournee_id = vals['tournee_id']
#         vals['plan_partner_ids'] = self._get_partner_ids()
#         vals['plan_planning_ids'] = self._get_planning_ids()
#        return super(OfTourneePlanification, self).create(vals)

#     @api.model
#     def default_get(self, fields_list):
#         u"""
#         La plupart des champs son récupérés depuis la tournée
#         """
#         tournee_obj = self.env['of.planning.tournee']
# 
#         tournee_ids = self._context.get('active_ids', [])
#         if tournee_ids:
# #             fields = ['date','date_jour','equipe_id','zip','city','distance','epi_lat','epi_lon']
# #             result = tournee_obj.read(tournee_ids[0], fields)
# #             result['equipe_id'] = result['equipe_id'][0]
# #             result['distance'] = result['distance'] or 20.0
# #             result['distance_add'] = result['distance'] + 10.0
#             tournee = tournee_obj.browse(tournee_ids)
#             result = {
#                 'plan_partner_ids' : self._get_partner_ids(tournee),
#                 'plan_planning_ids': self._get_planning_ids(tournee),
#                 'distance_add'     : tournee.distance + 10,
#             }
#         else:
#             result = {
# #                'equipe_id'   : False,
# #                'distance'    : 20.0,
#                 'distance_add': 30.0
#             }
# 
#         result = {key:val for key,val in result.iteritems() if key in fields_list}
#         missing_fields = [f for f in fields_list if f not in result]
#         result.update(super(OfTourneePlanification, self).default_get(missing_fields))
#         return result


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
                        for field in ['zip','city']:
                            if address[field]:
                                libelle += " "+address[field]
                        new_planning_list.append(self.make_planning(date_planifi_debut, date_planifi_fin, True,
                                                                    service=plan_partner.service_id, libelle=libelle))
                        hor_fin = date_planifi_fin
                        del plan_partners[index]
                        del date_planifi_list[0]
                        new_plan_partners.append((3,plan_partner.id))
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
                for field in ['zip','city']:
                    if address[field]:
                        libelle += " "+address[field]

                plan_plans.append(self.make_planning(new_hor_fin, (new_hor_fin + plan_partner.duree), True, 
                                                     service=plan_partner.service_id, libelle=libelle))
                new_hor_fin += plan_partner.duree
                last_geo_lat = address.geo_lat
                last_geo_lng = address.geo_lng
                new_plan_partners.append((3,plan_partner.id))

        if plan_plans:
            self.write({'plan_planning_ids': plan_plans, 'plan_partner_ids':new_plan_partners})
        return self._get_refresh_action()

#     @api.multi
#     def button_add_plan(self):
#         return self.button_planifier(False)

    @api.multi
    def creneau(self, creneau_avant, creneau_apres, start, end):
        modif_planning = []
        if creneau_apres:
            end = creneau_apres.date_flo_deadline
            modif_planning.append((3, creneau_apres.id))
        if creneau_avant:
            start = creneau_avant.date_flo
            modif_planning.append((3, creneau_avant.id))
        add_creneau = self.add_plan(start, end, False)
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
#                'partner_id': service.partner_id.id,
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

    @api.multi
    def button_confirm_old(self):
        intervention_obj = self.env['of.planning.intervention']

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        for plan in self:
            if not plan.plan_planning_ids:
                continue
            equipe = plan.equipe_id
            date_jour = plan.tournee_id.date
            datetime_val = fields.Datetime.from_string(date_jour)
            local_tz = timezone(self._context['tz'])
            utc = timezone('UTC')

            for planning in plan.plan_planning_ids:
                if (not planning.is_occupe) or planning.is_planifie:
                    continue

                date_datetime = datetime_val + timedelta(hours=planning.date_flo)
                date_datetime_local = local_tz.localize(date_datetime)
                date_datetime_sanszone = date_datetime_local.astimezone(utc)
                date_string = fields.Datetime.to_string(date_datetime_sanszone)

                partner = planning.partner_id
                tache = planning.tache_id
                description = ''
                if partner:
                    for service in partner.service_ids:
                        if tache.id == service.tache_id.id:
                            description += (tache.name + '\n') + (service.template_id and (service.template_id.name + '\n') or '') + (service.note or '')
                            break

                values = {
                    'hor_md'     : equipe.hor_md,
                    'hor_mf'     : equipe.hor_mf,
                    'hor_ad'     : equipe.hor_ad,
                    'hor_af'     : equipe.hor_af,
                    'part_id'    : partner and partner.id,
                    'tache_id'   : tache and tache.id or False,
                    'equipe_id'  : equipe.id,
                    'date'       : date_string,
                    'duree'      : planning.duree,
                    'user_id'    : self._uid,
                    'company_id' : partner and partner.partner_maga and partner.partner_maga.id or False,
                    'name'       : planning.name,
                    'state'      : 'Planifie',
                    'description': description,
                    'verif_dispo': True,
                }
                intervention_obj.create(values)

                # Mise a jour de la date minimale de prochaine intervention dans le service
                if planning.service_id and planning.date_next:
                    planning.service_id.write({'date_next': planning.date_next})
        return self._get_refresh_action()

#     # interdire la suppression ou addition des lignes de la table avec les RDVs
#     @api.onchange('plan_planning_ids_dis1')
#     def onchange_plannings(self):
#         planning_obj = self.env['of.tournee.planification.planning']
# 
#         id = False
#         ids = isinstance(ids, int or long) and [ids] or ids
#         if len(ids) != 0:
#             id = ids[0]
# 
#         planning_mod = []   # id, debut, duree, fin
#         for line in plan_planning_ids_dis:
#             if len(line) != 0:
#                 if line[0] == 1:
#                     if ('date_flo' in line[2].keys()) or ('duree' in line[2].keys()):
#                         if 'date_flo' in line[2].keys():
#                             planning_mod = [line[1], round(line[2]['date_flo'], 5)]
#                         else:
#                             planning_mod = [line[1], False]
#                         if 'duree' in line[2].keys():
#                             planning_mod.append(round(line[2]['duree'], 5))
#                         else:
#                             planning_mod.append(False)
# 
# 
#         # mise a jour la liste des RDVs
#         if planning_mod:
#             partner_address_id_old = False
#             partner_id_old = False
#             tache_old = False
#             libelle_old = ''
#             new_plan_planning_ids_dis = plan_planning_ids_dis[:]
#             if id:
#                 for l in self.browse(cr, uid, id).plan_planning_ids:
#                     if l.id == planning_mod[0]:
#                         if not planning_mod[1]:
#                             planning_mod[1] = l.date_flo or 0.0
#                         if not planning_mod[2]:
#                             planning_mod[2] = l.duree or 0.0
#                         planning_mod.append(planning_mod[2] + planning_mod[1])
#                         partner_address_id_old = l.partner_address_id and l.partner_address_id.id or False
#                         partner_id_old = l.partner_id and l.partner_id.id or False
#                         tache_old = l.tache and l.tache.id or False
#                         libelle_old = l.name or ''
# 
#                         # ajouter un creneau pour remplacer ancien RDV
#                         start = l.date_flo
#                         finish = l.date_flo_deadline
#                         creneau_after_existe_ids = planning_obj.search(cr, uid, [('date_flo', '=', finish), ('wizard_id', '=', l.wizard_id.id), ('is_occupe', '=', False)])
#                         creneau_before_existe_ids = planning_obj.search(cr, uid, [('date_flo_deadline', '=', start), ('wizard_id', '=', l.wizard_id.id), ('is_occupe', '=', False)])
#                         creneau_res = self.creneau(cr, uid, ids, creneau_after_existe_ids, creneau_before_existe_ids, start, finish)
# 
#                         del_ids = []
#                         for r in creneau_res:
#                             if r[0] == 3:
#                                 del_ids.append(r[1])
#                             new_plan_planning_ids_dis.append(r)
#                         del_ids.append(planning_mod[0])
#                         if len(del_ids) != 0:
#                             del_list = new_plan_planning_ids_dis[:]
#                             for dl in del_list:
#                                 if len(dl) >= 2:
#                                     if (dl[1] in del_ids) and (dl[0] != 3):
#                                         new_plan_planning_ids_dis.remove(dl)
#                                     if dl[1] == planning_mod[0]:
#                                         new_plan_planning_ids_dis.append((3, dl[1]))
#                         break
# 
#                 # tester si il y a un creneau pour nouveau horaire
#                 is_possible = False
#                 msgalert_pos = {'title':'Attention', 'message': 'Le nouvel horaire n\'est pas disponible'}
#                 add_plan_list = new_plan_planning_ids_dis[:]
#                 for a in add_plan_list:
#                     if len(a) != 0:
#                         if a[0] in (0, 4):
#                             if a[0] == 0:
#                                 s = round(a[2]['date_flo'], 5)
#                                 f = round(a[2]['date_flo_deadline'], 5)
#                             elif a[0] == 4:
#                                 obj_plan = planning_obj.browse(cr, uid, a[1])
#                                 s = obj_plan.date_flo
#                                 f = obj_plan.date_flo_deadline
#                             if (planning_mod[1] >= s) and (planning_mod[3] <= f):
#                                 is_possible = True
#                                 start_new = planning_mod[1]
#                                 finish_new = planning_mod[3]
#                                 duree_new = planning_mod[2]
#                                 if a[0] == 4:
#                                     new_plan_planning_ids_dis.append((3, a[1]))
#                                 elif a[0] == 0:
#                                     new_plan_planning_ids_dis.remove(a)
#                                 if start_new > s:
#                                     new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, s, start_new, False))
#                                 new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, start_new, finish_new, True, partner_address_id_old, partner_id_old, tache_old, duree_new, libelle_old))
#                                 if finish_new < f:
#                                     new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, finish_new, f, False))
#                 if not is_possible:
#                     return {'value': {'plan_planning_ids_dis1': plan_planning_ids},
#                             'warning': msgalert_pos}
#                 else:
# 
#                     # ajouter le creneau
#                     plan_planning_ids_dis = new_plan_planning_ids_dis[:]
# 
#         if id:
#             self.write(cr, uid, ids, {'plan_planning_ids': plan_planning_ids_dis})
#             cr.commit()   # sans commmit, on ne peut pas savoir si c'est l'utilisateur qui a fait la suppression ou le system qui la fait
#             new_plannings = []
#             for line in self.browse(cr, uid, id).plan_planning_ids:
#                 new_plannings.append((4, line.id))
#             return {'value': {'plan_planning_ids'     : new_plannings,
#                               'plan_planning_ids_dis1': new_plannings}}
#         else:
#             return {'value': {'plan_planning_ids': plan_planning_ids_dis}}
# 
#     # interdire la suppression ou addition des lignes de la table avec les RDVs
#     def onchange_plannings_old(self, cr, uid, ids, plan_planning_ids_dis, len_plannings, plan_planning_ids):
#         cr.commit()
#         planning_obj = self.pool.get('of.res.planification.planning')
# 
#         # si l'utilisateur fait la suppression
#         msgalert_del = {'title':'Attention', 'message': 'Il faut cliquer sur le bouton Supprimer pour enlever une ligne'}
#         if len(plan_planning_ids_dis) < len_plannings:
#             return {'value': {'plan_planning_ids_dis1': plan_planning_ids}, 'warning': msgalert_del}
# 
#         id = False
#         ids = isinstance(ids, int or long) and [ids] or ids
#         if len(ids) != 0:
#             id = ids[0]
# 
#         planning_mod = []   # id, debut, duree, fin
#         for line in plan_planning_ids_dis:
#             if len(line) != 0:
#                 if line[0] in (2, 3, 5):
#                     return {'value': {'plan_planning_ids_dis1': plan_planning_ids}, 'warning': msgalert_del}
#                 elif line[0] == 1:
#                     if ('date_flo' in line[2].keys()) or ('duree' in line[2].keys()):
#                         if 'date_flo' in line[2].keys():
#                             planning_mod = [line[1], round(line[2]['date_flo'], 5)]
#                         else:
#                             planning_mod = [line[1], False]
#                         if 'duree' in line[2].keys():
#                             planning_mod.append(round(line[2]['duree'], 5))
#                         else:
#                             planning_mod.append(False)
# 
# 
#         # mise a jour la liste des RDVs
#         if len(planning_mod) != 0:
#             partner_address_id_old = False
#             partner_id_old = False
#             tache_old = False
#             libelle_old = ''
#             new_plan_planning_ids_dis = plan_planning_ids_dis[:]
#             if id:
#                 for l in self.browse(cr, uid, id).plan_planning_ids:
#                     if l.id == planning_mod[0]:
#                         if not planning_mod[1]:
#                             planning_mod[1] = l.date_flo or 0.0
#                         if not planning_mod[2]:
#                             planning_mod[2] = l.duree or 0.0
#                         planning_mod.append(planning_mod[2] + planning_mod[1])
#                         partner_address_id_old = l.partner_address_id and l.partner_address_id.id or False
#                         partner_id_old = l.partner_id and l.partner_id.id or False
#                         tache_old = l.tache and l.tache.id or False
#                         libelle_old = l.name or ''
# 
#                         # ajouter un creneau pour remplacer ancien RDV
#                         start = l.date_flo
#                         finish = l.date_flo_deadline
#                         creneau_after_existe_ids = planning_obj.search(cr, uid, [('date_flo', '=', finish), ('wizard_id', '=', l.wizard_id.id), ('is_occupe', '=', False)])
#                         creneau_before_existe_ids = planning_obj.search(cr, uid, [('date_flo_deadline', '=', start), ('wizard_id', '=', l.wizard_id.id), ('is_occupe', '=', False)])
#                         creneau_res = self.creneau(cr, uid, ids, creneau_after_existe_ids, creneau_before_existe_ids, start, finish)
# 
#                         del_ids = []
#                         for r in creneau_res:
#                             if r[0] == 3:
#                                 del_ids.append(r[1])
#                             new_plan_planning_ids_dis.append(r)
#                         del_ids.append(planning_mod[0])
#                         if len(del_ids) != 0:
#                             del_list = new_plan_planning_ids_dis[:]
#                             for dl in del_list:
#                                 if len(dl) >= 2:
#                                     if (dl[1] in del_ids) and (dl[0] != 3):
#                                         new_plan_planning_ids_dis.remove(dl)
#                                     if dl[1] == planning_mod[0]:
#                                         new_plan_planning_ids_dis.append((3, dl[1]))
#                         break
# 
#                 # tester si il y a un creneau pour nouveau horaire
#                 is_possible = False
#                 msgalert_pos = {'title':'Attention', 'message': 'Le nouvel horaire n\'est pas disponible'}
#                 add_plan_list = new_plan_planning_ids_dis[:]
#                 for a in add_plan_list:
#                     if len(a) != 0:
#                         if a[0] in (0, 4):
#                             if a[0] == 0:
#                                 s = round(a[2]['date_flo'], 5)
#                                 f = round(a[2]['date_flo_deadline'], 5)
#                             elif a[0] == 4:
#                                 obj_plan = planning_obj.browse(cr, uid, a[1])
#                                 s = obj_plan.date_flo
#                                 f = obj_plan.date_flo_deadline
#                             if (planning_mod[1] >= s) and (planning_mod[3] <= f):
#                                 is_possible = True
#                                 start_new = planning_mod[1]
#                                 finish_new = planning_mod[3]
#                                 duree_new = planning_mod[2]
#                                 if a[0] == 4:
#                                     new_plan_planning_ids_dis.append((3, a[1]))
#                                 elif a[0] == 0:
#                                     new_plan_planning_ids_dis.remove(a)
#                                 if start_new > s:
#                                     new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, s, start_new, False))
#                                 new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, start_new, finish_new, True, partner_address_id_old, partner_id_old, tache_old, duree_new, libelle_old))
#                                 if finish_new < f:
#                                     new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, finish_new, f, False))
#                 if not is_possible:
#                     return {'value': {'plan_planning_ids_dis1': plan_planning_ids},
#                             'warning': msgalert_pos}
#                 else:
# 
#                     # ajouter le creneau
#                     plan_planning_ids_dis = new_plan_planning_ids_dis[:]
# 
#         if id:
#             self.write(cr, uid, ids, {'plan_planning_ids': plan_planning_ids_dis})
#             cr.commit()   # sans commmit, on ne peut pas savoir si c'est l'utilisateur qui a fait la suppression ou le system qui la fait
#             new_plannings = []
#             for line in self.browse(cr, uid, id).plan_planning_ids:
#                 new_plannings.append((4, line.id))
#             return {'value': {'plan_planning_ids'     : new_plannings,
#                               'plan_planning_ids_dis1': new_plannings}}
#         else:
#             return {'value': {'plan_planning_ids': plan_planning_ids_dis}}

#     @api.onchange('plan_partner_ids_dis1')
#     def onchange_partners(self):
#         partner_obj = self.env['of.tournee.planification.partner']
#         planning_obj = self.env['of.tournee.planification.planning']
# 
#         id = False
#         ids = isinstance(ids, int or long) and [ids] or ids
#         if len(ids) != 0:
#             id = ids[0]
# 
#         is_changed = False
#         is_possible = True
#         for p in plan_partner_ids_dis:
#             if len(p) != 0:
#                 if (p[0] == 0) and (len(p) == 3):
#                     if ('is_changed' in p[2].keys()) and ('date_flo' in p[2].keys()) and ('duree' in p[2].keys()):
#                         if p[2]['is_changed'] and p[2]['date_flo'] and p[2]['duree']:
#                             debut = round(p[2]['date_flo'], 5)
#                             fin = round(p[2]['date_flo'] + p[2]['duree'], 5)
#                             is_changed = True
#                             break
#                 elif (p[0] == 1) and (len(p) == 3):
#                     p_id = p[1]
#                     obj_partner = partner_obj.browse(cr, uid, p_id)
#                     date_flo = False
#                     duree = False
#                     if 'is_changed' in p[2].keys():
#                         if p[2]['is_changed']:
#                             if 'date_flo' in p[2].keys():
#                                 if p[2]['date_flo']:
#                                     date_flo = round(p[2]['date_flo'], 5)
#                             else:
#                                 date_flo = obj_partner.date_flo or 0
#                             if 'duree' in p[2].keys():
#                                 if p[2]['duree']:
#                                     duree = round(p[2]['duree'], 5)
#                             else:
#                                 duree = obj_partner.duree or 0
# 
#                             if date_flo and duree:
#                                 debut = date_flo
#                                 fin = debut + duree
#                                 is_changed = True
#                                 break
# 
#         if is_changed:
# 
#             # tester si il y les conflits dans la table partenaire
#             for l in plan_partner_ids_dis:
#                 if (l[0] == 4) and (len(l) > 2):
#                     l_id = l[1]
#                     obj_partner = partner_obj.browse(cr, uid, l_id)
#                     if obj_partner.date_flo and obj_partner.date_flo_deadline:
#                         if (fin <= obj_partner.date_flo) or (debut >= obj_partner.date_flo_deadline):
#                             pass
#                         else:
#                             is_possible = False
#                             msgalert = {'title':'Attention', 'message': u'cet horaire est déjà planifié pour d\'autres clients'}
#                             break
#                 elif (l[0] == 0) and (len(l) == 3):
#                     is_line_mod = False
#                     if 'is_changed' in l[2].keys():
#                         if l[2]['is_changed']:
#                             is_line_mod = True
#                     if not is_line_mod:
#                         if ('date_flo' in l[2].keys()) and ('date_flo_deadline' in l[2].keys()):
#                             if (fin <= round(l[2]['date_flo'], 5)) or (debut >= round(l[2]['date_flo_deadline'], 5)):
#                                 pass
#                             else:
#                                 is_possible = False
#                                 msgalert = {'title':'Attention', 'message': u'cet horaire est déjà planifié pour d\'autres clients'}
#                                 break
# 
#             # tester si il y a les creneaux dans la table planning
#             if is_possible:
#                 msgalert = {'title':'Attention', 'message': u'Il n\'y a pas de créneau pour cet horaire'}
#                 is_possible = False
#                 for plan in plan_planning_ids:
#                     if len(plan) != 0:
#                         plan_debut = False
#                         plan_fin = False
#                         if (plan[0] == 0) and (len(plan) == 3):
#                             if 'is_occupe' in plan[2].keys():
#                                 if not plan[2]['is_occupe']:
#                                     if ('date_flo' in plan[2].keys()) and ('date_flo_deadline' in plan[2].keys()):
#                                         plan_debut = round(plan[2]['date_flo'], 5)
#                                         plan_fin = round(plan[2]['date_flo_deadline'], 5)
#                             else:
#                                 if ('date_flo' in plan[2].keys()) and ('date_flo_deadline' in plan[2].keys()):
#                                     plan_debut = round(plan[2]['date_flo'], 5)
#                                     plan_fin = round(plan[2]['date_flo_deadline'], 5)
#                         elif (plan[0] == 4) and (len(plan) > 2):
#                             plan_id = plan[1]
#                             obj_plan = planning_obj.browse(cr, uid, plan_id)
#                             if not obj_plan.is_occupe:
#                                 plan_debut = obj_plan.date_flo or 0
#                                 plan_fin = obj_plan.date_flo_deadline or 0
#                         if plan_debut and plan_fin:
#                             if (debut >= plan_debut) and (fin <= plan_fin):
#                                 is_possible = True
#                                 break
# 
#         new_plan_partner_ids = plan_partner_ids[:]
#         i = 0
#         for pt in plan_partner_ids:
#             if len(pt) == 3:
#                 if pt[0] in (0, 1):
#                     if 'is_changed' in pt[2].keys():
#                         if pt[2]['is_changed']:
#                             new_plan_partner_ids[i][2]['is_changed'] = False
#             i += 1
# 
#         new_plan_partner_ids_dis = plan_partner_ids_dis[:]
#         i = 0
#         for pt in plan_partner_ids_dis:
#             if len(pt) == 3:
#                 if pt[0] in (0, 1):
#                     if 'is_changed' in pt[2].keys():
#                         if pt[2]['is_changed']:
#                             new_plan_partner_ids_dis[i][2]['is_changed'] = False
#             i += 1
# 
#         if not is_possible:
#             return {'value': {'plan_partner_ids_dis1': new_plan_partner_ids},
#                     'warning': msgalert}
#         else:
#             self.write(cr, uid, ids, {'plan_partner_ids': new_plan_partner_ids_dis})
# 
#             if id:
#                 new_partners = []
#                 for partner in self.plan_partner_ids:
#                     new_partners.append((4, partner.id))
#             else:
#                 new_partners = new_plan_partner_ids_dis[:]
#             return {'value': {'plan_partner_ids'     : new_partners,
#                               'plan_partner_ids_dis1': new_partners}}

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
    service_id = fields.Many2one('of.service', string="Service", required=True)

    partner_id = fields.Many2one(related='service_id.partner_id')
    partner_address_id = fields.Many2one(related='service_id.address_id')
    tache_id = fields.Many2one(related='service_id.tache_id')
    phone = fields.Char(compute='_get_phone')

#     partner_id = fields.Many2one('res.partner', string='Client', required=True)
#     partner_address_id = fields.Many2one('res.partner', string='Adresse', required=True)
#     tache_id = fields.Many2one('of.planning.tache', string='Intervention', required=True)
#     phone = fields.Char(string=u'Téléphone', size=128)

    tache_possible = fields.Many2many('of.planning.tache', related="wizard_id.tournee_id.equipe_id.tache_ids", string="Intervention Possible")

    duree = fields.Float(string=u'Durée', required=True, digits=(12, 5))
    distance = fields.Float(string='Dist.tot.', digits=(12, 3))
    dist_prec = fields.Float(string='Prec.', digits=(12,3))
    dist_suiv = fields.Float(string='Suiv', digits=(12,3))
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

#     # tester si l'horaire est possible
#     @api.onchange('date_flo')
#     def onchange_date_flo(self, cr, uid, ids, date_flo, duree, plan_planning_ids, plan_partner_ids):
#         planning_obj = self.pool.get('of.res.planification.planning')
#         partner_obj = self.pool.get('of.res.planification.partner')
# 
#         if date_flo:
#             is_possible = True
#             date_flo_deadline = round(date_flo + duree, 5)
# 
#             # tester si il y a conflit dans la table partnaire
#             for partner in plan_partner_ids:
#                 if len(partner) != 0:
#                     pre_debut = False
#                     pre_fin = False
#                     if (partner[0] == 0) and (len(partner) == 3):
#                         pre_debut = round(partner[2]['date_flo'], 5)
#                         pre_fin = round(partner[2]['date_flo_deadline'], 5)
#                     elif (partner[0] == 1) and (len(partner) == 3):
#                         pre_id = partner[1]
#                         obj_partner = partner_obj.browse(cr, uid, pre_id)
#                         if 'date_flo' in partner[2].keys():
#                             pre_debut = round(partner[2]['date_flo'], 5)
#                         else:
#                             pre_debut = obj_partner.date_flo or 0
#                         if 'date_flo_deadline' in partner[2].keys():
#                             pre_fin = round(partner[2]['date_flo_deadline'], 5)
#                         else:
#                             pre_fin = obj_partner.date_flo_deadline or 0
#                     elif (partner[0] == 4) and (len(partner) > 2):
#                         pre_id = partner[1]
#                         obj_partner = partner_obj.browse(cr, uid, pre_id)
#                         pre_debut = obj_partner.date_flo or 0
#                         pre_fin = obj_partner.date_flo_deadline or 0
#                     if pre_debut and pre_fin:
#                         if (date_flo_deadline <= pre_debut) or (date_flo >= pre_fin):
#                             pass
#                         else:
#                             is_possible = False
#                             break
# 
#             # tester si il y a les creneaux dans la table planning
#             if is_possible:
#                 is_possible = False
#                 for plan in plan_planning_ids:
#                     if len(plan) != 0:
#                         debut = False
#                         fin = False
#                         if (plan[0] == 0) and (len(plan) == 3):
#                             debut = round(plan[2]['date_flo'], 5)
#                             fin = round(plan[2]['date_flo_deadline'], 5)
#                         elif (plan[0] == 4) and (len(plan) > 2):
#                             id = plan[1]
#                             obj_plan = planning_obj.browse(cr, uid, id)
#                             debut = obj_plan.date_flo or 0
#                             fin = obj_plan.date_flo_deadline or 0
#                         if debut and fin:
#                             if (date_flo >= debut) and (date_flo_deadline <= fin):
#                                 is_possible = True
#                                 break
#             else:
#                 is_possible = False
# 
#             if not is_possible:
#                 msgalert = {'title':'Attention', 'message': u'Il n\'y a pas de créneau correspondant à cet horaire'}
#                 return {'value': {'date_flo': 0, 'date_flo_deadline': 0}, 'warning': msgalert}


class OfTourneePlanificationPlanning(models.TransientModel):
    _name = 'of.tournee.planification.planning'
    _description = u'Résultat de Planification de RDV'

    name = fields.Char(u'Libellé', size=128, required=True)
    wizard_id = fields.Many2one('of.tournee.planification', string="Planification")
    service_id = fields.Many2one('of.service', string="Service")

    tache_id = fields.Many2one('of.planning.tache', string='Intervention')
#    partner_id = fields.Many2one('res.partner', string='Client')
    partner_address_id = fields.Many2one('res.partner', string='Adresse')

    date_flo = fields.Float(string='RDV', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    duree = fields.Float(string=u'Durée', digits=(12, 5))
    is_occupe = fields.Boolean(string=u'Occupé')
    is_planifie = fields.Boolean(string=u'Déjà Planifié')
    service_id = fields.Many2one('of.service', string="Service", readonly=True)
    date_next = fields.Date(string=u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention")

#     _columns = {
#         'name'             : fields.char(u'Libellé', size=128, required=True),
#         'wizard_plan_id'   : fields.many2one('of.res.planification', string="Planification"),
#         'tache'            : fields.many2one('of.planning.tache', 'Intervention'),
#         'partner_id'       : fields.many2one('res.partner', 'Client', oldname='res_partner_id'),
#         'partner_address_id'   : fields.many2one('res.partner.address', 'Adresse', oldname='res_partner_address_id'),
#         'date_flo'         : fields.float('RDV', required=True, digits=(12, 5)),
#         'date_flo_deadline': fields.float('Date', required=True, digits=(12, 5)),
#         'duree'            : fields.float(u'Durée', digits=(12, 5)),
#         'is_occupe'        : fields.boolean('Occupe'),
#         'is_planifie'      : fields.boolean(u'Déjà Planifié'),
#         'service_id'       : fields.many2one('of.service', "Service", readonly=True),
#         'date_next'        : fields.date(u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention"),
#     }

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
                'partner_id': planning.partner_id.id,
                'partner_address_id': address.id,
                'phone': phone,
                'duree': planning.duree or 0.0,
                'tache_id': planning.tache_id and planning.tache_id.id or False,
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
                    partner.write({'dist_prec':0.0, 'dist_suiv':0.0, 'distance': distance_points(lat, lon, partner_lat, partner_lon)})
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
                    partner.write({'dist_prec':dist_prec, 'dist_suiv':dist_suiv, 'distance': dist_prec + dist_suiv})
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
