# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta

class OfService(models.Model):
    _inherit = "of.service"

    parc_installe_id = fields.Many2one('of.parc.installe', string=u"No de série",
        domain="partner_id and [('client_id', '=', partner_id), '|', ('site_adresse_id', '=', False), ('site_adresse_id', '=', address_id)] or "
               "address_id and [('client_id', 'parent_of', address_id), '|', ('site_adresse_id', '=', False), ('site_adresse_id', '=', address_id)] or []")

    parc_installe_product_id = fields.Many2one('product.product', string=u"Désignation", related="parc_installe_id.product_id", readonly=True)
    parc_installe_site_adresse_id = fields.Many2one('res.partner', string=u"Adresse de pose", related="parc_installe_id.site_adresse_id", readonly=True)
    parc_installe_note = fields.Text(string=u"Note", related="parc_installe_id.note", readonly=True)
    sav_id = fields.Many2one("project.issue", string="SAV", domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")

    @api.onchange('address_id')
    def _onchange_address_id(self):
        self.ensure_one()
        if self.address_id:
            parc_obj = self.env['of.parc.installe']
            if not parc_obj.check_access_rights('read', raise_exception=False):  # ne pas tenter le onchange si n'a pas les droits
                return
            parc_installe = parc_obj.search([('site_adresse_id', '=', self.address_id.id)], limit=1)
            if not parc_installe:
                parc_installe = parc_obj.search([('client_id', '=', self.address_id.id)], limit=1)
            if not parc_installe and self.partner_id:
                parc_installe = parc_obj.search([('client_id', '=', self.partner_id.id)], limit=1)
            if parc_installe:
                self.parc_installe_id = parc_installe

    @api.multi
    def get_action_view_interventions_context(self, context={}):
        context = super(OfService, self).get_action_view_interventions_context(context)
        context['default_parc_installe_id'] = self.parc_installe_id and self.parc_installe_id.id or False
        return context

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    parc_installe_id = fields.Many2one('of.parc.installe', string=u"Parc installé", domain="['|', '|', ('client_id', '=', partner_id), ('client_id', '=', address_id), ('site_adresse_id', '=', address_id)]")

    @api.multi
    def button_open_of_planning_intervention(self):
        if self.ensure_one():
            return {
                'name': 'of.planning.intervention.form',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.planning.intervention',
                'res_id': self._ids[0],
                'type': 'ir.actions.act_window',
            }

    @api.model
    def create(self, vals):
        service_obj = self.env['of.service']
        service = vals.get('service_id') and service_obj.browse(vals['service_id'])
        if service:
            vals['parc_installe_id'] = service.parc_installe_id and service.parc_installe_id.id
        return super(OfPlanningIntervention, self).create(vals)

class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    intervention_ids = fields.One2many('of.planning.intervention', 'parc_installe_id', string="Interventions")
    service_count = fields.Integer(compute="_get_service_count")
    a_programmer_count = fields.Integer(compute="_get_service_count")

    @api.multi
    def _get_service_count(self):
        """Smart button vue parc installé : renvoi le nombre de service lié à la machine installée"""
        service_obj = self.env['of.service']
        for parc in self:
            services = service_obj.search([('parc_installe_id', '=', parc.id)])  # permet de ne faire d'un seul search
            parc.service_count = len(services.filtered('recurrence'))
            parc.a_programmer_count = len(services.filtered(lambda s: not s.recurrence))

    @api.multi
    def action_view_service(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_service').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id), ('recurrence', '=', True)]
        action['context'] = {
        'default_partner_id': self.client_id.id,
        'default_address_id': self.site_adresse_id.id,
        'default_recurrence': True,
        'default_parc_installe_id': self.id,
        'default_origin': u"[parc installé] " + (self.name or ''),
        'bloquer_recurrence': True,
        }
        return action

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id), ('recurrence', '=', False)]
        action['context'] = {
        'default_partner_id': self.client_id.id,
        'default_address_id': self.site_adresse_id.id,
        'default_recurrence': False,
        'default_parc_installe_id': self.id,
        'default_origin': u"[parc installé] " + (self.name or ''),
        'bloquer_recurrence': True,
        }
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
#         action['active_id'] = False,
#         action['active_ids'] = [],
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
        'default_partner_id': self.client_id.id,
        'default_address_id': self.site_adresse_id.id,
        'default_recurrence': False,
        'default_date_next': today_str,
        'default_date_fin': deux_semaines_str,
        'default_parc_installe_id': self.id,
        'default_origin': u"[Parc installé] " + (self.name or ''),
        'bloquer_recurrence': True,
        }
        return action


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    of_a_programmer_count = fields.Integer(compute="_get_of_a_programmer_count")

    @api.multi
    def _get_of_a_programmer_count(self):
        """Smart button vue SAV : renvoi le nombre d'interventions à programmer liées à la machine installée"""
        service_obj = self.env['of.service']
        for sav in self:
            sav.of_a_programmer_count = len(service_obj.search([('sav_id', '=', sav.id), ('recurrence', '=', False)]))

    @api.multi
    def action_view_a_programmer(self):
        self.ensure_one()
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['domain'] = [('sav_id', '=', self.id), ('recurrence', '=', False)]
        action['context'] = {
        'default_partner_id': self.of_parc_installe_client_id.id,
        'default_address_id': self.of_parc_installe_lieu_id.id,
        'default_recurrence': False,
        'default_date_next': today_str,
        'default_date_fin': deux_semaines_str,
        'default_sav_id': self.id,
        'default_parc_installe_id': self.of_produit_installe_id.id,
        'default_origin': u"[SAV] " + self.name,
        'bloquer_recurrence': True,
        }
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
#         action['active_id'] = False,
#         action['active_ids'] = [],
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
        'default_partner_id': self.of_parc_installe_client_id.id,
        'default_address_id': self.of_parc_installe_lieu_id.id,
        'default_recurrence': False,
        'default_date_next': today_str,
        'default_date_fin': deux_semaines_str,
        'default_sav_id': self.id,
        'default_parc_installe_id': self.of_produit_installe_id.id,
        'default_origin': u"[SAV] " + self.name,
        'bloquer_recurrence': True,
        }
        return action
