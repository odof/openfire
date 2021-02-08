# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    @api.multi
    def _compute_of_a_programmer_count(self):
        """Dû aux changement des services on n'utilise plus le système de récurrence inclus dans le service."""
        service_obj = self.env['of.service']
        for sav in self:
            sav.of_a_programmer_count = len(service_obj.search([('sav_id', '=', sav.id)]))

    @api.multi
    def action_view_a_programmer(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_of_contract_service_form_planning').read()[0]
        action['domain'] = [('sav_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_sav').id,
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
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_sav').id,
            }
        return action
