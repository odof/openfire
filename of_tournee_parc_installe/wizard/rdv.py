# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import UserError

class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    @api.model
    def _default_partner(self):
        # Suivant que la prise de rdv se fait depuis le helpdesk ou le parc installé
        active_model = self._context.get('active_model', '')
        if active_model == 'of.parc.installe':
            partner_id = self.env['of.parc.installe'].browse(self._context['active_ids'][0]).client_id.id
        elif active_model == 'project.issue':
            partner_id = self.env['project.issue'].browse(self._context['active_ids'][0]).partner_id.id
        else:
            return super(OfTourneeRdv, self)._default_partner()

        partner = self.env['res.partner'].browse(partner_id)
        while partner.parent_id:
            partner = partner.parent_id
        return partner

    @api.model
    def _default_service(self):
        active_model = self._context.get('active_model', '')
        service = False
        if active_model == "of.parc.installe":
            sav = self._default_sav()
            # soit service soit sav
            if not sav:
                parc_installe = self.env['of.parc.installe'].browse(self._context['active_ids'][0])
                if parc_installe.service_count > 0:
                    service = self.env["of.service"].search([('parc_installe_id','=',parc_installe.id),('recurrence', '=', True)], limit=1)
        else:
            return super(OfTourneeRdv, self)._default_service()
        return service

    @api.model
    def _default_address(self):
        partner_obj = self.env['res.partner']
        active_model = self._context.get('active_model', '')
        if active_model == "of.parc.installe":
            partner = self.env['of.parc.installe'].browse(self._context['active_ids'][0]).client_id
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])
        elif active_model == "project.issue":
            partner = self.env['project.issue'].browse(self._context['active_ids'][0]).partner_id
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])
        else:
            return super(OfTourneeRdv, self)._default_address()

        if address and not (address.geo_lat or address.geo_lng):
            address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
                                          '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)],
                                         limit=1) or address
        return address or False

    @api.model
    def _default_sav(self):
        active_model = self._context.get('active_model', '')
        sav = False
        if active_model == 'project.issue':
            sav = self.env['project.issue'].browse(self._context['active_ids'][0])
        return sav

    sav_id = fields.Many2one('project.issue', string='SAV', default=lambda x: x._default_sav(), domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', partner_address_id)]")

    @api.multi
    def get_values_intervention_create(self):
        values = super(OfTourneeRdv, self).get_values_intervention_create()
        if self.sav_id:
            values['sav_id'] = self.sav_id.id
        return values
