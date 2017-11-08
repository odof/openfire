"""
from osv import fields, osv
from datetime import datetime, timedelta, date, time
import calendar
import math
from math import asin, sin, cos, sqrt, acos, radians




class of_res_add(osv.TransientModel):
    _name = 'of.res.add'
    
    def _get_partners(self, cr, uid, context=None):
        res_partner_obj = self.pool.get('res.partner')
        adr_obj = self.pool.get('res.partner.address')
        tache_obj = self.pool.get('of.planning.tache')
        res_plan_obj = self.pool.get('of.res.planification')
        service_obj = self.pool.get('of.service')
        planning_pose_obj = self.pool.get('of.planning.pose')
        
        partners = []
        
        # tous les competances de l'equipe
        if context is None:
            context = {}
        res_plan_ids = context.get('active_ids', [])
        if len(res_plan_ids) != 0:
            res_plan_id = res_plan_ids[0]
        obj_plan = res_plan_obj.browse(cr, uid, res_plan_id)
        tache_ids = []
        if obj_plan.equipe_id.tache_ids:
            for t in obj_plan.equipe_id.tache_ids:
                tache_ids.append(t.id)
                
        # tous les adresses existent
        client_existe_ids = []
        if obj_plan.plan_partner_ids:
            for pp in obj_plan.plan_partner_ids:
                client_existe_ids.append(pp.partner_id.id)
        if obj_plan.plan_planning_ids:
            for p in obj_plan.plan_planning_ids:
                if p.partner_id:
                    client_existe_ids.append(p.partner_id.id)
                    
        # tous les services correspondent les criteres
        product_ids = []
        for t in tache_obj.browse(cr, uid, tache_ids):
            if t.product_id:
                product_ids.append(t.product_id.id)
        date_res = obj_plan.date
        date_res_datetime = datetime.strptime(date_res, '%Y-%m-%d').date()
        date_mois = int(date_res_datetime.strftime('%m'))
        date_jour = date_res_datetime.isoweekday()
        date_annee = int(date_res_datetime.strftime('%Y'))
        mois_debut = date(date_annee, date_mois, 1)
        mois_fin = date(date_annee, date_mois, calendar.mdays[date_mois])
        mois_debut_str = mois_debut.strftime('%Y-%m-%d')
        mois_fin_str = mois_fin.strftime('%Y-%m-%d')
        service_ids = service_obj.search(cr, uid, [('product_id', 'in', tuple(product_ids))])
        service_ids_mj = []
        for service in service_obj.browse(cr, uid, service_ids):
            for m in service.mois_ids:
                if m.id == date_mois:
                    for j in service.jour_ids:
                        if j.id == date_jour:
                            service_ids_mj.append(service.id)
                            break
                    break
        partner_service_ids = []   # partner_id, service_id
        if len(service_ids_mj) != 0:
            for s in service_obj.browse(cr, uid, service_ids_mj):
                if s.partner_id:
                    partner_service_ids.append((s.partner_id.id, s.id))
        
        epi_lat_rad = math.radians(obj_plan.epi_lat)
        epi_lon_rad = math.radians(obj_plan.epi_lon)
        distance_add = obj_plan.distance_add
        distance_old = distance_add - 10.0
        
        if len(partner_service_ids) != 0:
            for partner_service_id in partner_service_ids:
                if partner_service_id[0] not in client_existe_ids:
                    obj_partner_service = service_obj.browse(cr, uid, partner_service_id[1])
                    service_product_id = obj_partner_service.product_id.id
                    service_tache_id = tache_obj.search(cr, uid, [('product_id', '=', service_product_id)])[0]
                    obj_service_tache = tache_obj.browse(cr, uid, service_tache_id)
                    
                    # tester si le service est deja planifie
                    pose_ids = planning_pose_obj.search(cr, uid, [('tache', '=', service_tache_id), ('part_id', '=', partner_service_id[0]), 
                                                                  ('date', '>=', mois_debut_str), ('date', '<=', mois_fin_str),
                                                                  ('state', 'not in', ('Reporte', 'Inacheve', 'Annule'))])
                    if len(pose_ids) == 0:
                        addr_id = res_partner_obj.address_get(cr, uid, [partner_service_id[0]], ['delivery'])['delivery']
                        adr = False
                        if addr_id:
                            addr = adr_obj.browse(cr, uid, addr_id)
                            if addr.gps_lat or addr.gps_lon:
                                adr = addr.id
                            else:
                                adr_ids = adr_obj.search(cr, uid, [('partner_id', '=', partner_service_id[0]), '|', ('gps_lat', '!=', 0), ('gps_lon', '!=', 0)])
                                adr = adr_ids and adr_ids[0] or False
                                if not adr:
                                    adr_ids = adr_obj.search(cr, uid, [('partner_id', '=', partner_service_id[0])])
                                    adr = adr_ids and adr_ids[0] or False
                        if adr:
                            
                            # tester si le client est dans la zone suplementaire de la tournee
                            obj_adr = adr_obj.browse(cr, uid, adr)
                            gps_lat_client_rad = math.radians(obj_adr.gps_lat)
                            gps_lon_client_rad = math.radians(obj_adr.gps_lon)
                            distance_points = 2*asin(sqrt((sin((epi_lat_rad-gps_lat_client_rad)/2)) ** 2 + cos(epi_lat_rad)*cos(gps_lat_client_rad)*(sin((epi_lon_rad-gps_lon_client_rad)/2)) ** 2)) * 6366
                            if (round(distance_points, 5) <= distance_add) and (round(distance_points, 5) > distance_old):
                                adr_o = adr_obj.browse(cr, uid, adr)
                                phone = adr_o.phone or ''
                                phone += adr_o.mobile and ((phone and ' || ' or '') + adr_o.mobile) or ''
                                partners.append((0, 0, {
                                    'partner_id': partner_service_id[0],
                                    'partner_adr_id': adr,
                                    'phone': phone,
                                    'duree': obj_service_tache.duree or 0.0,
                                    'tache': service_tache_id,
                                    'is_choose': False,
                                }))
        
        # mise a jour la valeur de distance maximum
        obj_plan.write({'distance_add': distance_add + 10.0})
        
        return partners
    
    _columns = {
        'add_partner_ids': fields.one2many('of.res.add.partner', 'wizard_add_id', 'Clients'),
    }
    
    _defaults = {
        'add_partner_ids': _get_partners,
    }
    
    def button_select(self, cr, uid, ids, context=None):
        plan_partner_obj = self.pool.get('of.res.planification.partner')
        tache_obj = self.pool.get('of.planning.tache')
        plan_obj = self.pool.get('of.res.planification')
        service_obj = self.pool.get('of.service')
        
        plan_id = False
        plan_ids = context.get('active_ids',[])
        if len(plan_ids) != 0:
            plan_id = plan_ids[0]
            
        tache_ids = []
        equipe = plan_obj.browse(cr, uid, plan_id).equipe_id
        if equipe.tache_ids:
            for t in equipe.tache_ids:
                tache_ids.append(t.id)
        product_ids = []
        for tache in tache_obj.browse(cr, uid, tache_ids):
            if tache.product_id:
                product_ids.append(tache.product_id.id)
          
        obj_plan = plan_obj.browse(cr, uid, plan_id)      
        date_res = obj_plan.date
        date_res_datetime = datetime.strptime(date_res, '%Y-%m-%d').date()
        date_mois = int(date_res_datetime.strftime('%m'))
        date_jour = date_res_datetime.isoweekday()
        
        for a in self.browse(cr, uid, ids, context=context):
            if a.add_partner_ids:
                for p in a.add_partner_ids:
                    if p.is_choose:
                        if p.partner_adr_id.gps_lat or p.partner_adr_id.gps_lon:
                            res_parter = p.partner_adr_id.partner_id
                            obj_service = False
                            service_product_id = False
                            if res_parter.service_ids:
                                for service in res_parter.service_ids:
                                    if service.product_id.id in product_ids:
                                        for mois in service.mois_ids:
                                            if mois.numero == date_mois:
                                                for jour in service.jour_ids:
                                                    if jour.numero == date_jour:
                                                        obj_service = service
                                                        service_product_id = service.product_id.id
                                                        break
                            if obj_service:
                                tache_id = tache_obj.search(cr, uid, [('product_id', '=', service_product_id)])[0]
                                obj_tache = tache_obj.browse(cr, uid, tache_id)
                                phone = p.partner_adr_id.phone or ''
                                phone += p.partner_adr_id.mobile and ((phone and ' || ' or '') + p.partner_adr_id.mobile) or ''
                                plan_partner_obj.create(cr, uid, {
                                    'partner_id': res_parter.id or False,
                                    'partner_adr_id': p.partner_adr_id.id,
                                    'phone': phone,
                                    'duree': obj_tache.duree or 0.0,
                                    'tache': tache_id,
                                    'is_choose': False,
                                    'wizard_plan_id': plan_id,
                                })
                        else:
                            raise osv.except_osv('Attention', str('Il faut configurer GPS pour le client ' + p.partner_adr_id.partner_id.name or ''))
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.res.planification',
            'type': 'ir.actions.act_window',
            'context': context,
            'res_id': plan_id,
        }
    
of_res_add()


class of_res_add_partner(osv.TransientModel):
    _name = 'of.res.add.partner'
    _description = 'Ajouter Partenaire de Planification de RDV'
    
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Client', required=True),
        'partner_adr_id': fields.many2one('res.partner.address', 'Adresse', required=True),
        'duree': fields.float(u'Dur\u00E9e', required=True, digits=(12, 5)),
        'tache': fields.many2one('of.planning.tache', 'Intervention', required=True),
        'is_choose': fields.boolean('Cocher'),
        'wizard_add_id': fields.many2one('of.res.add', string="Planification"),
    }
    
of_res_add_partner()
"""
