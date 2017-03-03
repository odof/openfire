# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta
import math
from math import cos
import pytz
from pytz import timezone
from odoo.addons.of_planning_tournee.of_planning_tournee import distance_points

class OfTourneePlanification(models.TransientModel):
    _name = 'of.tournee.planification'
    _description = 'Planification de RDV'

    @api.depends('tournee_id', 'tournee_id.date')
    def _get_date_display(self):
        for planif in self:
            date_tournee_datetime = fields.Date.from_string(planif.tournee_id.date)
            planif.date_display = date_tournee_datetime.strftime('%A %d %B %Y')

    @api.multi
    def _get_partner_ids(self, tournee):
        self.ensure_one()

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

        # Nous allons utiliser une requete sql dans un souci de performance
        query = "SELECT DISTINCT id\n" \
                "FROM res_partner\n" \
                "WHERE id IN %%s\n" \
                "AND asin(sqrt(pow(sin((radians(gps_lat)-(%s))/2.0),2) + cos(radians(gps_lat))*(%s)*pow(sin((radians(gps_lon)-(%s))/2.0),2))) < %s "

        
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
                    'partner_id': partner.id,
                    'phone': phone,
                    'duree': service_tache_duree or 0.0,
                    'tache': service.tache_id.id,
                    'tache_possible': taches._ids,
                }))
        return partners

    @api.multi
    def _get_planning_ids(self, tournee):
        self.ensure_one()

        res_obj = self.pool['of.res']
        intervention_obj = self.pool['of.planning.intervention']
        partner_obj = self.pool['res.partner']

        # toutes les competences de l'equipe
        if 'tz' not in self._context:
            self = self.with_context(dict(self._context, tz='Europe/Paris'))

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
                intervention_dates = []
                for intervention_date in (intervention.date, intervention.date_deadline):
                    try:
                        if len(intervention_date) > 19:
                            intervention_date = intervention_date[:19]
                    except: pass
                    date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention_date))
                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    date_local = max(date_local, date_min)
                    date_local = min(date_local, date_max)
                    
                    date_local_flo = round(date_local.hour +
                                           date_local.minute / 60.0 +
                                           date_local.second / 3600.0, 5)
                    intervention_dates.append(date_local_flo)
                intervention_partner_id = intervention.partner_id and intervention.partner_id.id or False
                hor_list.append(intervention_dates + [intervention.name, intervention.tache_id.id, intervention.duree, intervention_partner_id])

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
                debut_add_str, fini_add_str = res_obj.hours_to_strs([debut_add, eh[1]])
                while hor_list:
                    if hor_list[0][0] < eh[1]:
                        if debut_add < hor_list[0][0]:
                            debut_str, fini_str = res_obj.hours_to_strs([debut_add, hor_list[0][0]])
                            plannings.append((0, 0, {
                                'name': debut_str + '-' + fini_str,
                                'is_occupe': False,
                                'is_planifie': False,
                                'date_flo': debut_add,
                                'date_flo_deadline': hor_list[0][0],
                            }))
                        
                        plannings.append((0, 0, {
                            'name': hor_list[0][2],
                            'is_occupe': True,
                            'is_planifie': True,
                            'date_flo': hor_list[0][0],
                            'date_flo_deadline': hor_list[0][1],
                            'tache_id': hor_list[0][3],
                            'duree': hor_list[0][4],
                            'partner_id': hor_list[0][5],
                            'partner_adr_id': hor_list[0][6],
                        }))
                        debut_add = hor_list[0][1]
                        debut_add_str = res_obj.hours_to_strs([hor_list[0][1]])[0]
                        
                        del hor_list[0]
                    else:
                        break
                if eh[1] > debut_add:
                    plannings.append((0, 0, {
                        'name': debut_add_str + '-' + fini_add_str,
                        'is_occupe': False,
                        'is_planifie': False,
                        'date_flo': debut_add,
                        'date_flo_deadline': eh[1],
                    }))

        return plannings

    def _get_len_plannings(self, cr, uid, ids, name, args, contex=None):
        result = {}
        for planning in self.read(cr, uid, ids, ['plan_planning_ids']):
            result[planning['id']] = planning['plan_planning_ids'] and len(planning['plan_planning_ids']) or 0
        return result



    tournee_id = fields.Many2one('of.planning.tournee', string=u'Tournée')

    plan_partner_ids = fields.One2many('of.tournee.planification.partner', 'wizard_plan_id', string='Clients')
    plan_planning_ids = fields.One2many('of.tournee.planification.planning', 'wizard_plan_id', string='RDV')


    


    _columns = {
        'date'                  : fields.date('Date'),
        'date_jour'             : fields.char('Jour', size=24),
        'equipe_id'             : fields.many2one('of.planning.equipe', 'Equipe'),
        'zip'                   : fields.char('Code Postal', size=24),
        'city'                  : fields.char('Ville', size=128),
        'distance'              : fields.float('Eloignement (km)', digits=(12,3)),
        'plan_partner_ids'      : fields.one2many('of.res.planification.partner', 'wizard_plan_id', 'Clients'),
        'plan_partner_ids_dis1' : fields.related('plan_partner_ids', type='one2many', relation='of.res.planification.partner', string='Clients'),
        'plan_planning_ids'     : fields.one2many('of.res.planification.planning', 'wizard_plan_id', 'RDV'),
        'plan_planning_ids_dis1': fields.related('plan_planning_ids', type='one2many', relation='of.res.planification.planning', string='RDV', store=False),
        'len_plannings'         : fields.function(_get_len_plannings, method=True, type='integer'),
        'date_display'          : fields.char('RES Jour', size=64),
        'distance_add'          : fields.float('Eloignement maximum (km)', digits=(12,3)),
        'epi_lat'               : fields.float('Epicentre Lat', digits=(12, 12), required=True),
        'epi_lon'               : fields.float('Epicentre Lon', digits=(12, 12), required=True),
    }

    _defaults = {
        'date_display': _get_date_display,
        'plan_partner_ids': _get_partner_ids,
        'plan_planning_ids': _get_planning_ids,
    }

    @api.model
    def create(self, vals):
        tournee_id = vals['tournee_id']

        vals['plan_partner_ids'] = self._get_partner_ids()
        vals['plan_planning_ids'] = self._get_planning_ids()

        return super(OfTourneePlanification, self).create(vals)

    def default_get(self, fields_list):
        """
        La plupart des champs son recuperes depuis le planning_res
        """
        planning_res_obj = self.env['of.planning.res']
        if context is None:
            context = {}

        planning_res_ids = context.get('active_ids', [])
        if len(planning_res_ids) == 0:
            result = {
                'equipe_id'   : False,
                'distance'    : 20.0,
                'distance_add': 30.0
            }
        else:
            fields = ['date','date_jour','equipe_id','zip','city','distance','epi_lat','epi_lon']
            result = planning_res_obj.read(cr, uid, planning_res_ids[0], fields, context=context)
            result['equipe_id'] = result['equipe_id'][0]
            result['distance'] = result['distance'] or 20.0
            result['distance_add'] = result['distance'] + 10.0

        result = {key:val for key,val in result.iteritems() if key in fields_list}
        missing_fields = [f for f in fields_list if f not in result]
        result.update(super(of_res_planification, self).default_get(cr, uid, missing_fields, context=context))
        return result

    def planifier(self, cr, uid, ids, plan_partner_ids=False, context=None):
        """
        Planifie des rendez-vous en deplacant des clients de plan_partner_ids vers plan_planning_ids
        @param plan_partner_ids: Si defini, seuls les partenaires correspondants pourront etre deplaces
        """
        address_obj = self.pool.get('res.partner.address')

        if not ids:
            return False

        res_plan_id = isinstance(ids, (int,long)) and ids or ids[0]
        res_plan = self.browse(cr, uid, res_plan_id)
        equipe = res_plan.equipe_id
        plan_partners = []
        equipe_gps = []
        date_planifi_list = []   # debut, fin, line_id

        # Liste des creneaux
        planning_list = [(   # debut, fin, adr_id, latitude, longitude, line_id, is_planifie
            p_line.date_flo,
            p_line.date_flo_deadline,
            p_line.partner_adr_id and p_line.partner_adr_id.id or False,
            p_line.partner_adr_id and p_line.partner_adr_id.gps_lat or False,
            p_line.partner_adr_id and p_line.partner_adr_id.gps_lon or False,
            p_line.id,
            p_line.is_planifie or False)
        for p_line in res_plan.plan_planning_ids]

        if res_plan.plan_partner_ids:
            for line in res_plan.plan_partner_ids:
                if (plan_partner_ids is not False) and (line.id not in plan_partner_ids):
                    continue
                rp = line.partner_adr_id
                if not rp:
                    raise osv.except_osv('Attention', str(u"Vous n'avez pas configur\u00E9 le GPS du client " + (line.partner_id.name or '')))
                if rp.gps_lat or rp.gps_lon:
                    plan_partners.append(line)
                    if line.date_flo and line.date_flo_deadline and (plan_partner_ids is not False):
                        date_planifi_list.append([line.date_flo, line.date_flo_deadline, line.id])
        if not (equipe.gps_lat or equipe.gps_lon):
            raise osv.except_osv('Attention', u"Il faut configurer l'adresse de l'\u00E9quipe")
        equipe_gps = [equipe.gps_lat, equipe.gps_lon]
        if plan_partners:

            # tester si l'horaire de travail est defini correctement pour l'equipe
            if not planning_list:
                raise osv.except_osv('Attention', u'Il faut configurer les horaires de travail pour cette \u00E9quipe')

            plan_plans = []
            new_plan_partners = []

            new_planning_list = planning_list[:]
            if date_planifi_list:
                # Partenaires dans la liste plan_partner_ids (plan_partner_ids is not False)
                # Et dont un l'horaire a ete specifie. Leur placement est donc prioritaire sur les calculs de distances
                date_planifi_list.sort()
                for planning in planning_list:
                    if planning[2] or planning[6]:
                        # Deja planifie
                        continue
                    else:
                        # Creneau disponible
                        plan_plans.append((3, planning[5]))
                        new_planning_list.remove(planning)
                        hor_fini = planning[0]
                        while 1:
                            if (hor_fini >= planning[1]):
                                break
                            if not date_planifi_list:
                                add_creneau = self.add_plan(cr, uid, ids, hor_fini, planning[1], False)
                                new_planning_list.append(add_creneau)
                                break

                            # tester si il y a les dates planifies dans ce creneau
                            date_planifi_debut, date_planifi_fin, date_planifi_line_id = date_planifi_list[0]
                            if date_planifi_debut < planning[1]:
                                if date_planifi_debut != hor_fini:
                                    # L'heure de debut de la tache ne correspond pas au debut du creneau : on cree un creneau vide avant la tache
                                    add_creneau = self.add_plan(cr, uid, ids, hor_fini, date_planifi_debut, False)
                                    new_planning_list.append(add_creneau)
                                # Recuperation de la ligne du partenaire
                                index = 0
                                for plan_partner in plan_partners:
                                    if plan_partner.id == date_planifi_line_id:
                                        break
                                    index += 1
                                # Creation de la ligne de planning
                                partner = plan_partner.partner_id
                                address = plan_partner.partner_adr_id
                                libelle = partner.name
                                for field in ['zip','city']:
                                    if address[field]:
                                        libelle += " "+address[field]
                                add_plan = self.add_plan(cr, uid, ids, date_planifi_debut, date_planifi_fin, True,
                                                         address.id, partner.id, plan_partner.tache.id, plan_partner.duree, libelle)
                                new_planning_list.append(add_plan)
                                hor_fini = date_planifi_fin
                                del plan_partners[index]
                                del date_planifi_list[0]
                                new_plan_partners.append((3,plan_partner.id))
                            else:
                                # La tache est ulterieure au creneau : on comble l'horaire avec un nouveau creneau vide
                                add_creneau = self.add_plan(cr, uid, ids, hor_fini, planning[1], False)
                                new_planning_list.append(add_creneau)
                                break


            last_gps_lat = 0
            last_gps_lon = 0
            for new_planning in new_planning_list:
                # Placement de taches sur les creneaux disponibles en fonction de la distance a la tache precedente.
                is_planifi = False
                # Test de creneau deja attribue
                if len(new_planning) == 7:
                    if new_planning[2] or new_planning[6]:
                        is_planifi = True
                        if new_planning[3] or new_planning[4]:
                            last_gps_lat = new_planning[3]
                            last_gps_lon = new_planning[4]
                else:
                    if new_planning[2]['is_occupe']:
                        is_planifi = True
                        plan_plans.append(new_planning)
                        adr = address_obj.browse(cr, uid, new_planning[2]['partner_adr_id'])
                        last_gps_lat = adr.gps_lat or 0
                        last_gps_lon = adr.gps_lon or 0
                if is_planifi:
                    continue
                if not (last_gps_lat or last_gps_lon):
                    last_gps_lat,last_gps_lon = equipe_gps

                # Creneau disponible
                if len(new_planning) == 7:
                    plan_plans.append((3, new_planning[5]))
                    new_hor_fini = new_planning[0]
                    planning_deadline = new_planning[1]
                else:
                    new_hor_fini = new_planning[2]['date_flo']
                    planning_deadline = new_planning[2]['date_flo_deadline']
                while 1:
                    if (new_hor_fini >= planning_deadline):
                        break
                    if not plan_partners:
                        add_creneau = self.add_plan(cr, uid, ids, new_hor_fini, planning_deadline, False)
                        plan_plans.append(add_creneau)
                        break
                    min_distance = False

                    i = index = -1
                    for plan_partner in plan_partners:
                        i += 1
                        if new_hor_fini + plan_partner.duree > planning_deadline:
                            continue
                        address = plan_partner.partner_adr_id
                        distance = distance_points(last_gps_lat, last_gps_lon, address.gps_lat, address.gps_lon)
                        if min_distance is False or distance < min_distance:
                            min_distance = distance
                            index = i

                    if index == -1:
                        # Pas de client disponible pour le creneau restant (ou creneau vide)
                        add_creneau = self.add_plan(cr, uid, ids, new_hor_fini, planning_deadline, False)
                        plan_plans.append(add_creneau)
                        break

                    # Creation de la ligne de planning
                    plan_partner = plan_partners.pop(index)
                    partner = plan_partner.partner_id
                    address = plan_partner.partner_adr_id
                    libelle = partner.name
                    for field in ['zip','city']:
                        if address[field]:
                            libelle += " "+address[field]

                    add_plan = self.add_plan(cr, uid, ids, new_hor_fini, (new_hor_fini + plan_partner.duree), True, 
                                             address.id, partner.id, plan_partner.tache.id, plan_partner.duree, libelle)
                    plan_plans.append(add_plan)
                    new_hor_fini = new_hor_fini + plan_partner.duree
                    last_gps_lat = address.gps_lat
                    last_gps_lon = address.gps_lon
                    new_plan_partners.append((3,plan_partner.id))

            if len(plan_plans) != 0:
                res_plan.write({'plan_planning_ids': plan_plans, 'plan_partner_ids':new_plan_partners}, context=context)
        return True

    def button_add_plan(self, cr, uid, ids, context=None):
        self.planifier(cr, uid, ids, False, context=context)
        return True

    def creneau(self, cr, uid, ids, creneau_after_existe_ids, creneau_before_existe_ids, start, finish, context=None):
        planning_obj = self.pool.get('of.res.planification.planning')

        modif_planning = []
        if len(creneau_after_existe_ids) != 0:
            creneau_after_existe_id = creneau_after_existe_ids[0]
            creneau_after_existe = planning_obj.browse(cr, uid, creneau_after_existe_id, context=context)
            finish = creneau_after_existe.date_flo_deadline
            modif_planning.append((3, creneau_after_existe_id))
        if len(creneau_before_existe_ids) != 0:
            creneau_before_existe_id = creneau_before_existe_ids[0]
            creneau_before_existe = planning_obj.browse(cr, uid, creneau_before_existe_id, context=context)
            start = creneau_before_existe.date_flo
            modif_planning.append((3, creneau_before_existe_id))
        add_creneau = self.add_plan(cr, uid, ids, start, finish, False, context=context)
        modif_planning.append(add_creneau)
        return modif_planning

    def add_plan(self, cr, uid, ids, hor_debut, hor_fini, is_occupe, partner_adr_id=False, partner_id=False, tache=False, duree=0.0, libelle=False, context=None):
        res_obj = self.pool['of.res']
        adr_obj = self.pool['res.partner.address']
        tache_obj = self.pool['of.planning.tache']
        service_obj = self.pool['of.service']

        hor_debut_str, hor_fini_str = res_obj.hours_to_strs([hor_debut, hor_fini])
        phone = ''
        if partner_adr_id:
            adr_o = adr_obj.browse(cr, uid, partner_adr_id, context=context)
            phone += adr_o.phone or ''
            phone += adr_o.mobile and ((phone and ' || ' or '') + adr_o.mobile) or ''

        service_id = False
        date_next = False
        if tache and partner_adr_id:
            product_id = tache_obj.read(cr, uid, tache, ['product_id'], context=context)['product_id'][0]
            service_ids = service_obj.search(cr, uid, [('partner_adr_id','=',partner_adr_id),('product_id','=',product_id),('state','=','progress')], context=context)
            if service_ids:
                services = service_obj.browse(cr, uid, service_ids, context=context)
                if len(services) > 1:
                    # Si plusieurs services sont disponibles, ce qui ne devrait pas arriver, on prend le plus en retard
                    service = min(services, key=lambda s:s.date_next)
                else:
                    service = services[0]
                service_id = service.id

                wiz = self.browse(cr, uid, ids[0], context=context)
                date_next = service.get_next_date(wiz.date)
        return (0, 0, {
                'date_flo': hor_debut,
                'date_flo_deadline': hor_fini,
                'name': libelle or (hor_debut_str + '-' + hor_fini_str),
                'is_occupe': is_occupe,
                'is_planifie': False,
                'partner_adr_id': partner_adr_id,
                'phone': phone,
                'partner_id': partner_id,
                'tache': tache,
                'duree': duree,
                'service_id': service_id,
                'date_next': date_next,
                })

    def button_plan_auto(self, cr, uid, ids, context=None):
        self.planifier(cr, uid, ids, context=context)
        return True

    def button_confirm(self, cr, uid, ids, context=None):
        pose_obj = self.pool.get('of.planning.pose')

        if 'tz' not in context.keys():
            context['tz'] = 'Europe/Paris'

        for plan in self.browse(cr, uid, ids, context=context):
            if plan.plan_planning_ids:
                equipe = plan.equipe_id
                hor_md = equipe.hor_md
                hor_mf = equipe.hor_mf
                hor_ad = equipe.hor_ad
                hor_af = equipe.hor_af
                date_jour = plan.date
                datetime_val = datetime.strptime(date_jour, '%Y-%m-%d')
                local_tz = timezone(context['tz'])
                utc = timezone('UTC')
                verif_existe = False
                # si champ verif_dispo existe dans table of_planning_pose (module of_zz_kerbois), on le defini comme True
                cr.execute("SELECT * FROM information_schema.columns WHERE table_name='of_planning_pose' and column_name='verif_dispo'")
                if cr.fetchone():
                    verif_existe = True

                for planning in plan.plan_planning_ids:
                    if (not planning.is_planifie) and planning.is_occupe:
                        date_datetime = datetime_val + timedelta(hours=planning.date_flo)
                        date_datetime_local = local_tz.localize(date_datetime)
                        date_datetime_sanszone = date_datetime_local.astimezone(utc)
                        date_string = date_datetime_sanszone.strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            if len(date_string) > 19:
                                date_string = date_string[:19]
                        except: pass
                        part_id = planning.partner_id and planning.partner_id.id or False
                        tache_id = planning.tache and planning.tache.id or False
                        description = ''
                        if part_id and tache_id:
                            part = planning.partner_id
                            tache = planning.tache
                            if tache.product_id:
                                if part.service_ids:
                                    for ser in part.service_ids:
                                        tache_product_id = ser.product_id.id
                                        if tache.product_id.id == tache_product_id:
                                            description += (tache.name + '\n') + (ser.template_id and (ser.template_id.name + '\n') or '') + (ser.note or '')
                                            break

                        values = {
                            'hor_md': hor_md,
                            'hor_mf': hor_mf,
                            'hor_ad': hor_ad,
                            'hor_af': hor_af,
                            'part_id': part_id,
                            'tache': tache_id,
                            'poseur_id': equipe.id,
                            'date': date_string,
                            'duree': planning.duree,
                            'user_id': uid,
                            'magasin': planning.partner_id and planning.partner_id.partner_maga and planning.partner_id.partner_maga.id \
                                       or False,
                            'name': planning.name,
                            'state': 'Planifie',
                            'description': description,
                        }
                        if verif_existe:
                            values.update({'verif_dispo': True})

                        pose_id = pose_obj.create(cr, uid, values)
                        value = pose_obj.onchange_date(cr, uid, pose_id, date_string, values['duree'], values['hor_md'], values['hor_mf'],\
                                                        values['hor_ad'], values['hor_af'], False, False, context)
                        if value['value'].get('date_deadline', False):
                            pose_obj.write(cr, uid, pose_id, {'date_deadline': value['value']['date_deadline']})

                        # Mise a jour de la date minimale de prochaine intervention dans le service
                        if planning.service_id and planning.date_next:
                            planning.service_id.write({'date_next': planning.date_next})

        return {
            'name': u'Pr\u00E9paration du planning',
            'view_mode': 'tree,form',
            'res_model': 'of.planning.res',
            'type': 'ir.actions.act_window',
            'context': context,
        }

    # interdire la suppression ou addition des lignes de la table avec les RDVs
    def onchange_plannings(self, cr, uid, ids, plan_planning_ids_dis, len_plannings, plan_planning_ids):
        cr.commit()
        planning_obj = self.pool.get('of.res.planification.planning')

        # si l'utilisateur fait la suppression
        msgalert_del = {'title':'Attention', 'message': 'Il faut cliquer sur le bouton Supprimer pour enlever une ligne'}
        if len(plan_planning_ids_dis) < len_plannings:
            return {'value': {'plan_planning_ids_dis1': plan_planning_ids}, 'warning': msgalert_del}

        id = False
        ids = isinstance(ids, int or long) and [ids] or ids
        if len(ids) != 0:
            id = ids[0]

        planning_mod = []   # id, debut, duree, fin
        for line in plan_planning_ids_dis:
            if len(line) != 0:
                if line[0] in (2, 3, 5):
                    return {'value': {'plan_planning_ids_dis1': plan_planning_ids}, 'warning': msgalert_del}
                elif line[0] == 1:
                    if ('date_flo' in line[2].keys()) or ('duree' in line[2].keys()):
                        if 'date_flo' in line[2].keys():
                            planning_mod = [line[1], round(line[2]['date_flo'], 5)]
                        else:
                            planning_mod = [line[1], False]
                        if 'duree' in line[2].keys():
                            planning_mod.append(round(line[2]['duree'], 5))
                        else:
                            planning_mod.append(False)


        # mise a jour la liste des RDVs
        if len(planning_mod) != 0:
            partner_adr_id_old = False
            partner_id_old = False
            tache_old = False
            libelle_old = ''
            new_plan_planning_ids_dis = plan_planning_ids_dis[:]
            if id:
                for l in self.browse(cr, uid, id).plan_planning_ids:
                    if l.id == planning_mod[0]:
                        if not planning_mod[1]:
                            planning_mod[1] = l.date_flo or 0.0
                        if not planning_mod[2]:
                            planning_mod[2] = l.duree or 0.0
                        planning_mod.append(planning_mod[2] + planning_mod[1])
                        partner_adr_id_old = l.partner_adr_id and l.partner_adr_id.id or False
                        partner_id_old = l.partner_id and l.partner_id.id or False
                        tache_old = l.tache and l.tache.id or False
                        libelle_old = l.name or ''

                        # ajouter un creneau pour remplacer ancien RDV
                        start = l.date_flo
                        finish = l.date_flo_deadline
                        creneau_after_existe_ids = planning_obj.search(cr, uid, [('date_flo', '=', finish), ('wizard_plan_id', '=', l.wizard_plan_id.id), ('is_occupe', '=', False)])
                        creneau_before_existe_ids = planning_obj.search(cr, uid, [('date_flo_deadline', '=', start), ('wizard_plan_id', '=', l.wizard_plan_id.id), ('is_occupe', '=', False)])
                        creneau_res = self.creneau(cr, uid, ids, creneau_after_existe_ids, creneau_before_existe_ids, start, finish)

                        del_ids = []
                        for r in creneau_res:
                            if r[0] == 3:
                                del_ids.append(r[1])
                            new_plan_planning_ids_dis.append(r)
                        del_ids.append(planning_mod[0])
                        if len(del_ids) != 0:
                            del_list = new_plan_planning_ids_dis[:]
                            for dl in del_list:
                                if len(dl) >= 2:
                                    if (dl[1] in del_ids) and (dl[0] != 3):
                                        new_plan_planning_ids_dis.remove(dl)
                                    if dl[1] == planning_mod[0]:
                                        new_plan_planning_ids_dis.append((3, dl[1]))
                        break

                # tester si il y a un creneau pour nouveau horaire
                is_possible = False
                msgalert_pos = {'title':'Attention', 'message': 'Le nouvel horaire n\'est pas disponible'}
                add_plan_list = new_plan_planning_ids_dis[:]
                for a in add_plan_list:
                    if len(a) != 0:
                        if a[0] in (0, 4):
                            if a[0] == 0:
                                s = round(a[2]['date_flo'], 5)
                                f = round(a[2]['date_flo_deadline'], 5)
                            elif a[0] == 4:
                                obj_plan = planning_obj.browse(cr, uid, a[1])
                                s = obj_plan.date_flo
                                f = obj_plan.date_flo_deadline
                            if (planning_mod[1] >= s) and (planning_mod[3] <= f):
                                is_possible = True
                                start_new = planning_mod[1]
                                finish_new = planning_mod[3]
                                duree_new = planning_mod[2]
                                if a[0] == 4:
                                    new_plan_planning_ids_dis.append((3, a[1]))
                                elif a[0] == 0:
                                    new_plan_planning_ids_dis.remove(a)
                                if start_new > s:
                                    new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, s, start_new, False))
                                new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, start_new, finish_new, True, partner_adr_id_old, partner_id_old, tache_old, duree_new, libelle_old))
                                if finish_new < f:
                                    new_plan_planning_ids_dis.append(self.add_plan(cr, uid, ids, finish_new, f, False))
                if not is_possible:
                    return {'value': {'plan_planning_ids_dis1': plan_planning_ids},
                            'warning': msgalert_pos}
                else:

                    # ajouter le creneau
                    plan_planning_ids_dis = new_plan_planning_ids_dis[:]

        if id:
            self.write(cr, uid, ids, {'plan_planning_ids': plan_planning_ids_dis})
            cr.commit()   # sans commmit, on ne peut pas savoir si c'est l'utilisateur qui a fait la suppression ou le system qui la fait
            new_plannings = []
            for line in self.browse(cr, uid, id).plan_planning_ids:
                new_plannings.append((4, line.id))
            return {'value': {'plan_planning_ids'     : new_plannings,
                              'plan_planning_ids_dis1': new_plannings}}
        else:
            return {'value': {'plan_planning_ids': plan_planning_ids_dis}}

    def onchange_partners(self, cr, uid, ids, plan_partner_ids_dis, plan_partner_ids, plan_planning_ids):
        partner_obj = self.pool.get('of.res.planification.partner')
        planning_obj = self.pool.get('of.res.planification.planning')

        id = False
        ids = isinstance(ids, int or long) and [ids] or ids
        if len(ids) != 0:
            id = ids[0]

        is_changed = False
        is_possible = True
        for p in plan_partner_ids_dis:
            if len(p) != 0:
                if (p[0] == 0) and (len(p) == 3):
                    if ('is_changed' in p[2].keys()) and ('date_flo' in p[2].keys()) and ('duree' in p[2].keys()):
                        if p[2]['is_changed'] and p[2]['date_flo'] and p[2]['duree']:
                            debut = round(p[2]['date_flo'], 5)
                            fin = round(p[2]['date_flo'] + p[2]['duree'], 5)
                            is_changed = True
                            break
                elif (p[0] == 1) and (len(p) == 3):
                    p_id = p[1]
                    obj_partner = partner_obj.browse(cr, uid, p_id)
                    date_flo = False
                    duree = False
                    if 'is_changed' in p[2].keys():
                        if p[2]['is_changed']:
                            if 'date_flo' in p[2].keys():
                                if p[2]['date_flo']:
                                    date_flo = round(p[2]['date_flo'], 5)
                            else:
                                date_flo = obj_partner.date_flo or 0
                            if 'duree' in p[2].keys():
                                if p[2]['duree']:
                                    duree = round(p[2]['duree'], 5)
                            else:
                                duree = obj_partner.duree or 0

                            if date_flo and duree:
                                debut = date_flo
                                fin = debut + duree
                                is_changed = True
                                break

        if is_changed:

            # tester si il y les conflits dans la table partenaire
            for l in plan_partner_ids_dis:
                if (l[0] == 4) and (len(l) > 2):
                    l_id = l[1]
                    obj_partner = partner_obj.browse(cr, uid, l_id)
                    if obj_partner.date_flo and obj_partner.date_flo_deadline:
                        if (fin <= obj_partner.date_flo) or (debut >= obj_partner.date_flo_deadline):
                            pass
                        else:
                            is_possible = False
                            msgalert = {'title':'Attention', 'message': u'cet horaire est d\u00E9j\u00E0 planifi\u00E9 pour d\'autres clients'}
                            break
                elif (l[0] == 0) and (len(l) == 3):
                    is_line_mod = False
                    if 'is_changed' in l[2].keys():
                        if l[2]['is_changed']:
                            is_line_mod = True
                    if not is_line_mod:
                        if ('date_flo' in l[2].keys()) and ('date_flo_deadline' in l[2].keys()):
                            if (fin <= round(l[2]['date_flo'], 5)) or (debut >= round(l[2]['date_flo_deadline'], 5)):
                                pass
                            else:
                                is_possible = False
                                msgalert = {'title':'Attention', 'message': u'cet horaire est d\u00E9j\u00E0 planifi\u00E9 pour d\'autres clients'}
                                break

            # tester si il y a les creneaux dans la table planning
            if is_possible:
                msgalert = {'title':'Attention', 'message': u'Il n\'y a pas de cr\u00E9neau pour cet horaire'}
                is_possible = False
                for plan in plan_planning_ids:
                    if len(plan) != 0:
                        plan_debut = False
                        plan_fin = False
                        if (plan[0] == 0) and (len(plan) == 3):
                            if 'is_occupe' in plan[2].keys():
                                if not plan[2]['is_occupe']:
                                    if ('date_flo' in plan[2].keys()) and ('date_flo_deadline' in plan[2].keys()):
                                        plan_debut = round(plan[2]['date_flo'], 5)
                                        plan_fin = round(plan[2]['date_flo_deadline'], 5)
                            else:
                                if ('date_flo' in plan[2].keys()) and ('date_flo_deadline' in plan[2].keys()):
                                    plan_debut = round(plan[2]['date_flo'], 5)
                                    plan_fin = round(plan[2]['date_flo_deadline'], 5)
                        elif (plan[0] == 4) and (len(plan) > 2):
                            plan_id = plan[1]
                            obj_plan = planning_obj.browse(cr, uid, plan_id)
                            if not obj_plan.is_occupe:
                                plan_debut = obj_plan.date_flo or 0
                                plan_fin = obj_plan.date_flo_deadline or 0
                        if plan_debut and plan_fin:
                            if (debut >= plan_debut) and (fin <= plan_fin):
                                is_possible = True
                                break

        new_plan_partner_ids = plan_partner_ids[:]
        i = 0
        for pt in plan_partner_ids:
            if len(pt) == 3:
                if pt[0] in (0, 1):
                    if 'is_changed' in pt[2].keys():
                        if pt[2]['is_changed']:
                            new_plan_partner_ids[i][2]['is_changed'] = False
            i += 1

        new_plan_partner_ids_dis = plan_partner_ids_dis[:]
        i = 0
        for pt in plan_partner_ids_dis:
            if len(pt) == 3:
                if pt[0] in (0, 1):
                    if 'is_changed' in pt[2].keys():
                        if pt[2]['is_changed']:
                            new_plan_partner_ids_dis[i][2]['is_changed'] = False
            i += 1

        if not is_possible:
            return {'value': {'plan_partner_ids_dis1': new_plan_partner_ids},
                    'warning': msgalert}
        else:
            self.write(cr, uid, ids, {'plan_partner_ids': new_plan_partner_ids_dis})

            if id:
                new_partners = []
                for partner in self.browse(cr, uid, id).plan_partner_ids:
                    new_partners.append((4, partner.id))
            else:
                new_partners = new_plan_partner_ids_dis[:]
            return {'value': {'plan_partner_ids'     : new_partners,
                              'plan_partner_ids_dis1': new_partners}}

    def write(self, cr, uid, ids, vals, context=None):
        if 'plan_planning_ids_dis1' in vals.keys():
            del vals['plan_planning_ids_dis1']
        if 'plan_planning_ids_dis2' in vals.keys():
            del vals['plan_planning_ids_dis2']
        return super(of_res_planification, self).write(cr, uid, ids, vals, context=context)
of_res_planification()

class of_res_planification_partner(osv.TransientModel):
    _name = 'of.res.planification.partner'
    _description = 'Partenaire de Planification de RDV'

    def _get_tache_possible(self, cr, uid, ids, field, args, context=None):
        result = {}
        for plan_partner in self.browse(cr, uid, ids):
            tache_ids = []
            if plan_partner.wizard_plan_id and plan_partner.wizard_plan_id.equipe_id:
                for tache in plan_partner.wizard_plan_id.equipe_id.tache_ids:
                    if not tache.id in tache_ids:
                        tache_ids.append(tache.id)
            result[plan_partner.id] = tache_ids
        return result

    _columns = {
        'wizard_plan_id'   : fields.many2one('of.res.planification', string="Planification"),
        'partner_id'       : fields.many2one('res.partner', 'Client', required=True, oldname='res_partner_id'),
        'partner_adr_id'   : fields.many2one('res.partner.address', 'Adresse', required=True, oldname='res_partner_adr_id'),
        'tache'            : fields.many2one('of.planning.tache', 'Intervention', required=True),
        'tache_possible'   : fields.function(_get_tache_possible, method=True, type='one2many', obj='of.planning.tache', string="Intervention Possible"),
        'duree'            : fields.float(u'Dur\u00E9e', required=True, digits=(12, 5)),
        'distance'         : fields.float('Dist.tot.', digits=(12, 3)),
        'dist_prec'        : fields.float('Prec.', digits=(12,3)),
        'dist_suiv'        : fields.float('Suiv', digits=(12,3)),
        'date_flo'         : fields.float('RDV', digits=(12, 5)),
        'date_flo_deadline': fields.float('Date', digits=(12, 5)),
        'phone'            : fields.char(u'T\u00E9l\u00E9phone', size=128),
        'is_changed'       : fields.boolean('Modifie'),   # seulement quand on modifie la duree ou la date debut, c'est egale True
    }

    _defaults = {
        'is_changed': False,
    }

    _order = "distance, id"

    def button_add_plan(self, cr, uid, ids, context=None):
        plan = self.browse(cr, uid, ids[0], context=context).wizard_plan_id
        plan.planifier(ids, context=context)
        return True

    def onchange_tache_duree(self, cr, uid, ids, duree, date_flo=False):
        values = {'is_changed': True}
        if duree and date_flo:
            date_flo_deadline = round(date_flo + duree, 5)
            values['date_flo_deadline'] = date_flo_deadline
        return {'value': values}

    # tester si l'horaire est possible
    def onchange_date_flo(self, cr, uid, ids, date_flo, duree, plan_planning_ids, plan_partner_ids):
        planning_obj = self.pool.get('of.res.planification.planning')
        partner_obj = self.pool.get('of.res.planification.partner')

        if date_flo:
            is_possible = True
            date_flo_deadline = round(date_flo + duree, 5)

            # tester si il y a conflit dans la table partnaire
            for partner in plan_partner_ids:
                if len(partner) != 0:
                    pre_debut = False
                    pre_fin = False
                    if (partner[0] == 0) and (len(partner) == 3):
                        pre_debut = round(partner[2]['date_flo'], 5)
                        pre_fin = round(partner[2]['date_flo_deadline'], 5)
                    elif (partner[0] == 1) and (len(partner) == 3):
                        pre_id = partner[1]
                        obj_partner = partner_obj.browse(cr, uid, pre_id)
                        if 'date_flo' in partner[2].keys():
                            pre_debut = round(partner[2]['date_flo'], 5)
                        else:
                            pre_debut = obj_partner.date_flo or 0
                        if 'date_flo_deadline' in partner[2].keys():
                            pre_fin = round(partner[2]['date_flo_deadline'], 5)
                        else:
                            pre_fin = obj_partner.date_flo_deadline or 0
                    elif (partner[0] == 4) and (len(partner) > 2):
                        pre_id = partner[1]
                        obj_partner = partner_obj.browse(cr, uid, pre_id)
                        pre_debut = obj_partner.date_flo or 0
                        pre_fin = obj_partner.date_flo_deadline or 0
                    if pre_debut and pre_fin:
                        if (date_flo_deadline <= pre_debut) or (date_flo >= pre_fin):
                            pass
                        else:
                            is_possible = False
                            break

            # tester si il y a les creneaux dans la table planning
            if is_possible:
                is_possible = False
                for plan in plan_planning_ids:
                    if len(plan) != 0:
                        debut = False
                        fin = False
                        if (plan[0] == 0) and (len(plan) == 3):
                            debut = round(plan[2]['date_flo'], 5)
                            fin = round(plan[2]['date_flo_deadline'], 5)
                        elif (plan[0] == 4) and (len(plan) > 2):
                            id = plan[1]
                            obj_plan = planning_obj.browse(cr, uid, id)
                            debut = obj_plan.date_flo or 0
                            fin = obj_plan.date_flo_deadline or 0
                        if debut and fin:
                            if (date_flo >= debut) and (date_flo_deadline <= fin):
                                is_possible = True
                                break
            else:
                is_possible = False

            if not is_possible:
                msgalert = {'title':'Attention', 'message': u'Il n\'y a pas de cr\u00E9neau correspondant cet horaire'}
                return {'value': {'date_flo': 0, 'date_flo_deadline': 0}, 'warning': msgalert}
of_res_planification_partner()


class of_res_planification_planning(osv.TransientModel):
    _name = 'of.res.planification.planning'
    _description = 'Resultat de Planification de RDV'

    _columns = {
        'name'             : fields.char(u'Libell\u00E9', size=128, required=True),
        'wizard_plan_id'   : fields.many2one('of.res.planification', string="Planification"),
        'tache'            : fields.many2one('of.planning.tache', 'Intervention'),
        'partner_id'       : fields.many2one('res.partner', 'Client', oldname='res_partner_id'),
        'partner_adr_id'   : fields.many2one('res.partner.address', 'Adresse', oldname='res_partner_adr_id'),
        'date_flo'         : fields.float('RDV', required=True, digits=(12, 5)),
        'date_flo_deadline': fields.float('Date', required=True, digits=(12, 5)),
        'duree'            : fields.float(u'Dur\u00E9e', digits=(12, 5)),
        'is_occupe'        : fields.boolean('Occupe'),
        'is_planifie'      : fields.boolean(u'D\u00E9j\u00E0 Planifi\u00E9'),
        'service_id'       : fields.many2one('of.service', "Service", readonly=True),
        'date_next'        : fields.date(u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention"),
    }

    _order = "date_flo"

    def button_del_plan(self, cr, uid, ids, context=None):
        for planning in self.browse(cr, uid, ids, context=context):
            if planning.is_planifie:
                # Ne devrait pas arriver car le bouton suppression des plannings confirmes est masque
                raise osv.except_osv('Attention', u'Les RDVs d\u00E9j\u00E0 planifi\u00E9s se suppriment depuis le planning de pose')
            if not planning.partner_adr_id:
                # Ne devrait pas arriver car le bouton suppression des creneaux est masque
                raise osv.except_osv('Attention', u'Vous ne pouvez pas supprimer les cr\u00E9neaux')

            # ajouter dans la table partenaire
            phone = planning.partner_adr_id.phone or ''
            phone += planning.partner_adr_id.mobile and ((phone and ' || ' or '') + planning.partner_adr_id.mobile) or ''
            add_partner = [(0, 0, {
                'partner_id': planning.partner_id and planning.partner_id.id or False,
                'partner_adr_id': planning.partner_adr_id.id,
                'phone': phone,
                'duree': planning.duree or 0.0,
                'tache': planning.tache and planning.tache.id or False,
            })]
            # supprimer le planning
            modif_planning= [(3, planning.id)]

            # ajouter creneau et verifier si il y a les creneaux a fusionner
            start = planning.date_flo
            finish = planning.date_flo_deadline
            plan = planning.wizard_plan_id

            creneau_after_existe_ids = self.search(cr, uid, [('date_flo', '=', planning.date_flo_deadline), ('wizard_plan_id', '=', plan.id), ('is_occupe', '=', False)])
            creneau_before_existe_ids = self.search(cr, uid, [('date_flo_deadline', '=', planning.date_flo), ('wizard_plan_id', '=', plan.id), ('is_occupe', '=', False)])
            cre_res = plan.creneau(creneau_after_existe_ids, creneau_before_existe_ids, start, finish)
            modif_planning = modif_planning + cre_res

            plan.write({'plan_partner_ids': add_partner, 'plan_planning_ids': modif_planning})
        return True

    def button_trier(self, cr, uid, ids, context=None):
        planning = self.browse(cr, uid, ids, context=context)[0]
        plan = planning.wizard_plan_id
        if planning.is_occupe:
            address = planning.partner_adr_id
            lat = address.gps_lat
            lon = address.gps_lon
            for partner in plan.plan_partner_ids:
                partner_lat = partner.partner_adr_id.gps_lat
                partner_lon = partner.partner_adr_id.gps_lon
                if partner_lat or partner_lon:
                    partner.write({'dist_prec':0.0, 'dist_suiv':0.0, 'distance': distance_points(lat, lon, partner_lat, partner_lon)})
                else:
                    raise osv.except_osv('Attention', str(u"Vous n'avez pas configur\u00E9 le GPS du client " + (partner.partner_id.name or '')))
        else:
            # On a clique sur une case sans rendez-vous, on va donc chercher en fonction des rendez-vous qui l'encadrent.
            # Si il n'y a pas de rendez-vous avant ou apres, on se basera sur l'adresse du poseur
            p_prec = False
            gotcha = False
            for p_suiv in plan.plan_planning_ids:
                if gotcha:
                    break
                elif p_suiv == planning:
                    p_suiv = False
                    gotcha = True
                else:
                    p_prec = p_suiv

            p_suiv = p_suiv.partner_adr_id if p_suiv else (p_prec and plan.equipe_id)
            p_prec = p_prec.partner_adr_id if p_prec else plan.equipe_id

            p_lat = p_prec.gps_lat
            p_lon = p_prec.gps_lon
            if p_suiv:
                s_lat = p_suiv.gps_lat
                s_lon = p_suiv.gps_lon

            for partner in plan.plan_partner_ids:
                partner_lat = partner.partner_adr_id.gps_lat
                partner_lon = partner.partner_adr_id.gps_lon

                if partner_lat or partner_lon:
                    dist_prec = distance_points(p_lat, p_lon, partner_lat, partner_lon)
                    dist_suiv = p_suiv and distance_points(s_lat, s_lon, partner_lat, partner_lon) or 0.0
                    partner.write({'dist_prec':dist_prec, 'dist_suiv':dist_suiv, 'distance': dist_prec + dist_suiv})
                else:
                    raise osv.except_osv('Attention', str(u"Vous n'avez pas configur\u00E9 le GPS du client " + (partner.partner_id.name or '')))
        return True

    def button_confirm(self, cr, uid, ids, context=None):
        pose_obj = self.pool.get('of.planning.pose')

        if 'tz' not in context.keys():
            context['tz'] = 'Europe/Paris'

        for planning in self.browse(cr, uid, ids, context=context):
            if planning.is_planifie:
                # Ne devrait pas arriver car le bouton suppression des plannings confirmes est masque
                continue
            if not planning.is_occupe:
                # Ne devrait pas arriver car le bouton suppression des creneaux est masque
                continue

            plan = planning.wizard_plan_id
            equipe = plan.equipe_id
            date_jour = plan.date
            datetime_val = datetime.strptime(date_jour, '%Y-%m-%d')
            local_tz = timezone(context['tz'])
            utc = timezone('UTC')
            verif_existe = False
            # si champ verif_dispo existe dans table of_planning_pose (module of_zz_kerbois), on le definit comme True
            cr.execute("SELECT * FROM information_schema.columns WHERE table_name='of_planning_pose' and column_name='verif_dispo'")
            if cr.fetchone():
                verif_existe = True

            date_datetime = datetime_val + timedelta(hours=planning.date_flo)
            date_datetime_local = local_tz.localize(date_datetime)
            date_datetime_sanszone = date_datetime_local.astimezone(utc)
            date_string = date_datetime_sanszone.strftime("%Y-%m-%d %H:%M:%S")
            try:
                if len(date_string) > 19:
                    date_string = date_string[:19]
            except: pass
            part = planning.partner_id
            tache = planning.tache
            description = ''
            if part and tache and tache.product_id:
                tache_product_id = tache.product_id.id
                for ser in part.service_ids:
                    if ser.product_id.id == tache_product_id:
                        description += (tache.name + '\n') + (ser.template_id and (ser.template_id.name + '\n') or '') + (ser.note or '')
                        break

            values = {
                'hor_md'     : equipe.hor_md,
                'hor_mf'     : equipe.hor_mf,
                'hor_ad'     : equipe.hor_ad,
                'hor_af'     : equipe.hor_af,
                'part_id'    : part and part.id or False,
                'tache'      : tache and tache.id or False,
                'poseur_id'  : equipe.id,
                'date'       : date_datetime_sanszone,
                'duree'      : planning.duree,
                'user_id'    : uid,
                'magasin'    : part and part.partner_maga and part.partner_maga.id or False,
                'name'       : planning.name,
                'state'      : 'Planifie',
                'description': description,
            }
            if verif_existe:
                values.update({'verif_dispo': True})

            pose_id = pose_obj.create(cr, uid, values)
            value = pose_obj.onchange_date(cr, uid, pose_id, date_string, values['duree'], values['hor_md'], values['hor_mf'],\
                                            values['hor_ad'], values['hor_af'], False, False, context)
            if value['value'].get('date_deadline', False):
                pose_obj.write(cr, uid, pose_id, {'date_deadline': value['value']['date_deadline']})

            # Mise a jour de la date minimale de prochaine intervention dans le service
            if planning.service_id and planning.date_next:
                planning.service_id.write({'date_next': planning.date_next})

            planning.write({'is_planifie': True}, context=context)
        return True
of_res_planification_planning()