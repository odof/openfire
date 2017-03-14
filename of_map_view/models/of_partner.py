# -*- coding: utf-8 -*-

import json
from operator import itemgetter
from odoo import api, fields, models, tools, _

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    # 
    def get_company_lat_lng(self):
        if not self.company_id :
            return None
        else : 
            return [self.company_id.geo_lat, self.company_id.geo_lng]
        
    
    @api.model
    def get_locations_layer_data(self, domain=[]):
        #make a list of partners from a given domain, default to all partners
        partners = self.search(domain)
        locations = []
        for partner in partners:
            #maybe make locations a dictionary instead of a list?
            #if (partner.country_id.code.upper() == 'FR'): # workaround for testing
            location = [
                partner.geo_lat, partner.geo_lng, partner.id, partner.name, partner.street
                ]
            locations.append(location)
        
        locations.sort(key=itemgetter(1,0))   # sort by lng then lat
            
        return locations
    
    @api.model
    def get_default_map_config(self):
        # get default map center configuration
        IC = self.env['ir.config_parameter']
        deflt_c_lat = float(IC.get_param('Map_Default_Center_Latitude'))
        deflt_c_lng = float(IC.get_param('Map_Default_Center_Longitude'))
        deflt_zoom = int(IC.get_param('Map_Default_Zoom'))

        return [[deflt_c_lat, deflt_c_lng], deflt_zoom]
    
