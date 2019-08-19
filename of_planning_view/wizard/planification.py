# -*- coding: utf-8 -*-

from odoo import api, models, fields
#from datetime import datetime, timedelta, date as d_date
#import pytz
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
#import urllib

#import requests

"""ROUTING_BASE_URL = "http://s-hotel.openfire.fr:5000/"
ROUTING_VERSION = "v1"
ROUTING_PROFILE = "driving" """

def hours_to_strs(*hours):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return tuple("%02dh%02d" % (hour, round((hour % 1) * 60)) for hour in hours)

class OfPlanificationCreneau(models.TransientModel):
    _name = 'of.planification.creneau'
    _description = u'Prise de RDV depuis un créneau disponible'
    """
    @api.model
    def _default_partner(self):
        # Suivant que la prise de rdv se fait depuis la fiche client ou un service
        if self._context.get('active_model', '') == 'res.partner':
            partner_id = self._context['active_ids'][0]
        elif self._context.get('active_model', '') == 'of.service':
            partner_id = self.env['of.service'].browse(self._context['active_ids'][0]).partner_id.id
        else:
            return False

        partner = self.env['res.partner'].browse(partner_id)
        while partner.parent_id:
            partner = partner.parent_id
        return partner

    @api.model
    def _default_service(self):
        active_model = self._context.get('active_model', '')
        service = False
        if active_model == "of.service":
            service_id = self._context['active_ids'][0]
            service = self.env["of.service"].browse(service_id)
        elif active_model == "res.partner":
            partner = self._default_partner()
            if partner:
                service = self.env['of.service'].search([('partner_id', '=', partner.id)], limit=1)
        return service

    @api.model
    def _default_address(self):
        partner_obj = self.env['res.partner']
        active_model = self._context.get('active_model', '')
        if active_model == "of.service":
            service = self.env["of.service"].browse(self._context['active_ids'][0])
            partner = service.partner_id
            address = service.address_id
        elif active_model == "res.partner":
            partner = partner_obj.browse(self._context['active_ids'][0])
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])

        if address and not (address.geo_lat or address.geo_lng):
            address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
                                          '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)],
                                         limit=1) or address
        return address or False
    """
    heure_debut = fields.Float(string=u'Heude de début', digits=(5, 5))
    heure_fin = fields.Float(string=u'Heude de fin', digits=(5, 5))
