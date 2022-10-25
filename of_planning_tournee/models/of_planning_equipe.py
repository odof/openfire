# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OfPlanningEquipe(models.Model):  # @todo: vérifier si nécessaire
    _inherit = "of.planning.equipe"

    address_id = fields.Many2one('res.partner', string=u'Adresse de départ')
    address_retour_id = fields.Many2one('res.partner', string='Adresse de retour')
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        if self.employee_ids:
            self.address_id = self.employee_ids[0].address_home_id
            self.address_retour_id = self.address_id

    @api.onchange('address_id')
    def _onchange_address_id(self):
        if self.address_id:
            self.address_retour_id = self.address_id
