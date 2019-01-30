# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfService(models.Model):
    _inherit = "of.service"

    parc_installe_id = fields.Many2one('of.parc.installe', string=u"No de série", domain="[('client_id', '=', partner_id)]")
    parc_installe_product_id = fields.Many2one('product.product', string=u"Désignation", related="parc_installe_id.product_id", readonly=True)
    parc_installe_site_adresse_id = fields.Many2one('res.partner', string=u"Adresse de pose", related="parc_installe_id.site_adresse_id", readonly=True)
    parc_installe_note = fields.Text(string=u"Note", related="parc_installe_id.note", readonly=True)

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    parc_installe_id = fields.Many2one('of.parc.installe', string=u"Parc installé")

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

class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    intervention_ids = fields.One2many('of.planning.intervention', 'parc_installe_id', string="Interventions")
    service_count = fields.Integer(compute="_get_service_count")

    @api.multi
    def _get_service_count(self):
        """Smart button vue parc installé : renvoi le nombre de service lié à la machine installée"""
        service_obj = self.env['of.service']
        for parc in self:
            parc.service_count = len(service_obj.search([('parc_installe_id', '=', parc.id)]))

    @api.multi
    def action_view_service(self):
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_service').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id)]
        return action
