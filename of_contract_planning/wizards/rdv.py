# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'
    _description = u'Prise de RDV dans les tournées'

#     def _get_partner(self):
#         if self._context.get('active_model', '') == 'res.partner':
#             partner_id = self._context['active_ids'][0]
#         elif self._context.get('active_model', '') == 'of.service':
#             partner_id = self.env['of.service'].browse(self._context['active_ids'][0]).partner_id.id
#         elif self._context.get('active_model', '') == 'of.contract':
#             contract = self.env['of_contract'].brwose(self._context.get('active_id'))
#             if contract:
#                 lines = contract.service_ids.filtered('tache_id').sorted('date_next')
#                 if lines:
#                     lines
#                 else:
#                     partner_id = contract.partner_id.id
#             else:
#                 return False
#         else:
#             return False
# 
#         partner = self.env['res.partner'].browse(partner_id)
#         while partner.parent_id:
#             partner = partner.parent_id
#         return partner
# 
#     def _get_service(self):
#         pass
# 
#     @api.model
#     def _default_partner(self):
#         # Suivant que la prise de rdv se fait depuis la fiche client ou un service
#         if self._context.get('active_model', '') == 'res.partner':
#             partner_id = self._context['active_ids'][0]
#         elif self._context.get('active_model', '') == 'of.service':
#             partner_id = self.env['of.service'].browse(self._context['active_ids'][0]).partner_id.id
#         else:
#             return False
# 
#         partner = self.env['res.partner'].browse(partner_id)
#         while partner.parent_id:
#             partner = partner.parent_id
#         return partner
# 
#     @api.model
#     def _default_service(self):
#         active_model = self._context.get('active_model', '')
#         if active_model == "of.service":
#             service_id = self._context['active_ids'][0]
#             service = self.env["of.service"].browse(service_id)
#             return service
#         elif active_model == "res.partner":
#             service_obj = self.env['of.service']
#             partner = self._default_partner()
#             if not partner:
#                 return False
#             services = service_obj.search([('partner_id', '=', partner.id)], limit=1)
#             return services
#         else:
#             return False
# 
#     @api.model
#     def _default_address(self):
#         partner_obj = self.env['res.partner']
#         active_model = self._context.get('active_model', '')
#         if active_model == "of.service":
#             service_id = self._context['active_ids'][0]
#             service = self.env["of.service"].browse(service_id)
#             address_id = service.address_id.id
#         elif active_model == "res.partner":
#             partner = partner_obj.browse(self._context['active_ids'][0])
#             address_id = partner.address_get(['delivery'])['delivery']
# 
#         if address_id:
#             address = partner_obj.browse(address_id)
#             if not (address.geo_lat or address.geo_lng):
#                 address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
#                                               '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)], limit=1)
#                 if not address:
#                     address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id)])
#             return address
#         return False