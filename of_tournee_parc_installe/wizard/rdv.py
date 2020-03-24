# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import UserError


class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    @api.model
    def default_get(self, fields=None):
        res = super(OfTourneeRdv, self).default_get(fields)
        active_model = self._context.get('active_model', '')
        partner_obj = self.env['res.partner']
        service = False
        if active_model == 'of.parc.installe':
            parc_installe = self.env['of.parc.installe'].browse(self._context['active_ids'][0])
            partner = parc_installe.client_id
            partner_id = partner.id
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])

            if parc_installe.service_count > 0:
                service = self.env["of.service"].search(
                    [('parc_installe_id', '=', parc_installe.id), ('recurrence', '=', True)], limit=1)
            sav = False
        elif active_model == 'project.issue':
            sav = self.env['project.issue'].browse(self._context['active_ids'][0])
            partner = sav.partner_id
            partner_id = partner.id
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])
        else:
            return res

        if address and not (address.geo_lat or address.geo_lng):
            address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
                                          '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)],
                                         limit=1) or address

        partner = self.env['res.partner'].browse(partner_id)
        while partner.parent_id:
            partner = partner.parent_id

        res['partner_id'] = partner.id
        res['partner_address_id'] = address and address.id or False
        res['sav_id'] = sav and sav.id or False
        res['service_id'] = service and service.id or False
        return res

    sav_id = fields.Many2one('project.issue', string='SAV',
                             domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', partner_address_id)]")

    @api.multi
    def get_values_intervention_create(self):
        values = super(OfTourneeRdv, self).get_values_intervention_create()
        if self.sav_id:
            values['sav_id'] = self.sav_id.id
        return values
