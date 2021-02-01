# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    @api.multi
    def _compute_service_count(self):
        """
        Dû aux changement des services on n'utilise plus le système de récurrence inclus dans le service.
        Les deux champs donnent donc le même résultat.
        """
        service_obj = self.env['of.service']
        for parc in self:
            services = service_obj.search([('parc_installe_id', '=', parc.id)])  # permet de ne faire d'un seul search
            parc.service_count = len(services)
            parc.a_programmer_count = len(services)

    @api.multi
    def action_view_service(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_of_contract_service_form_planning').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_maintenance').id,
            }
        return action

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_contract_custom.action_of_contract_service_form_planning').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id)]
        action['context'] = {
            'default_partner_id'      : self.client_id.id,
            'default_address_id'      : self.site_adresse_id.id,
            'default_recurrence'      : False,
            'default_date_next'       : fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin'          : u"[parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_maintenance').id,
            }
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_of_contract_service_form_planning').read()[0]
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_contract_custom.view_of_contract_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[Parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_maintenance').id,
            }
        return action
