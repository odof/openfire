"""
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################


from osv import fields, osv
from datetime import datetime, timedelta, date, time
import math
from math import asin, sin, cos, sqrt, acos, radians



class of_search_partner(osv.osv_memory):
    _name = 'of.search.partner'
    _description = u'Recherche géolocalisée des clients'
    
    _columns = {
        'epi_lat': fields.float('Epicentre Lat', digits=(12, 12), required=True),
        'epi_lon': fields.float('Epicentre Lon', digits=(12, 12), required=True),
        'ville': fields.many2one('of.commune', 'Code Postal & Ville'),
        'zip': fields.char('Zip', size=24),
        'city': fields.char('City', size=128),
        'distance': fields.float('Eloignement (km)', digits=(12,4), required=True),
        'with_service': fields.boolean('Avec Service'),
        'without_service': fields.boolean('Sans Service'),
    }
    
    _defaults = {
        'with_service': False,
        'without_service': True,
        'distance': lambda *a: 20.0,
    }
    
    def onchange_ville(self, cr, uid, ids, ville):
        commune_obj = self.pool.get('of.commune')
        data = {}
        if ville:
            commune = commune_obj.read(cr, uid, ville, ['zip','city','gps_lat','gps_lon'])
            data['zip'] = commune['zip']
            data['city'] = commune['city']
            data['epi_lat'] = commune['gps_lat']
            data['epi_lon'] = commune['gps_lon']
            data['ville'] = ville
        else:
            data = {
                'zip' : '',
                'city': '',
                'ville': ville,
            }
        return {'value':data}
    
    def button_search(self, cr, uid, ids, context={}, *args):
        partner_obj = self.pool.get('res.partner')
        adr_obj = self.pool.get('res.partner.address')
        mod_obj = self.pool.get('ir.model.data')
        
        ids = ids and (isinstance(ids, (int or long)) and [ids] or ids) or ids
        if ids:
            for sear in self.browse(cr, uid, ids):
                with_service = sear.with_service
                without_service = sear.without_service
                epi_lat = sear.epi_lat
                epi_lon = sear.epi_lon
                epi_lat_rad = math.radians(epi_lat)
                epi_lon_rad = math.radians(epi_lon)
                distance = sear.distance
                date_today_str = datetime.now().date().strftime('%Y-%m-%d')
                
                # tous les clients actives
                all_partner_ids = partner_obj.search(cr, uid, [('active', '=', True), ('customer', '=', True)])
                
                # supprimer tous les distances des partenaire pour mettre les nouvelles valeurs
                cr.execute("UPDATE res_partner SET distance = NULL")
                
                # chercher tous les clients (adresse livraison) avec service valide dans ce secteur
                # service valide: service en cours
                if with_service and (not without_service):
                    cr.execute("SELECT DISTINCT partner_id from of_service WHERE state='progress'")
                    partner_service_ids = map(lambda x: x[0], cr.fetchall())
                    partner_confirm_ids = list(set(partner_service_ids) & set(all_partner_ids))
                    
                # tous les clients sans services ou avec service annule
                elif without_service and (not with_service):
                    cr.execute("SELECT DISTINCT partner_id from of_service WHERE state='progress'")
                    partner_service_ids = map(lambda x: x[0], cr.fetchall())
                    partner_confirm_ids = list(set(all_partner_ids) - set(partner_service_ids))
                else:
                    partner_confirm_ids = all_partner_ids
                
                # verifier l'adresse de livraison du client est dans le secteur
                partner_ids = []
                for partner_confirm_id in partner_confirm_ids:
                    addr_id = partner_obj.address_get(cr, uid, [partner_confirm_id], ['delivery'])['delivery']
                    adr = False
                    if addr_id:
                        addr = adr_obj.browse(cr, uid, addr_id)
                        if addr.gps_lat or addr.gps_lon:
                            adr = addr
                    if adr:
                        gps_lat_client_rad = math.radians(adr.gps_lat)
                        gps_lon_client_rad = math.radians(adr.gps_lon)
                        distance_points = 2*asin(sqrt((sin((epi_lat_rad-gps_lat_client_rad)/2)) ** 2 + cos(epi_lat_rad)*cos(gps_lat_client_rad)*(sin((epi_lon_rad-gps_lon_client_rad)/2)) ** 2)) * 6366
                        if distance_points <= distance:
                            partner_ids.append(partner_confirm_id)
                            partner_obj.write(cr, uid, partner_confirm_id, {'distance': distance_points})
                                
                res = mod_obj.get_object_reference(cr, uid, 'of_planning_tournee', 'of_res_view_partner_tree')
                res_id = res and res[1] or False,
                res_id = list(res_id)
                res_id = res_id[0]
                res_search = mod_obj.get_object_reference(cr, uid, 'base', 'view_res_partner_filter')
                res_search_id = res_search and res_search[1] or False,
                res_search_id = list(res_search_id)
                res_search_id = res_search_id[0]
                return {
                    'name': 'Clients',
                    'view_mode': 'tree,form',
                    'res_model': 'res.partner',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': "[('id','in',["+','.join(map(str, partner_ids))+"])]",
                    'nodestroy': True,
                    'search_view_id': res_search_id,
                    'views': [(res_id,'tree'),(False,'form')],
                }
        return True
    
of_search_partner()
"""
