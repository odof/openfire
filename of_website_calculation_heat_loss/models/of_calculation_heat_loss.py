# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFCalculationHeatLoss(models.Model):
    _inherit = 'of.calculation.heat.loss'

    partner_firstname = fields.Char(string=u"Prénom", related='partner_id.firstname')
    partner_lastname = fields.Char(string=u"Nom", related='partner_id.lastname')

    @api.model
    def get_altitude_ids_from_zip(self, zip):
        if not zip:
            return []
        department_obj = self.env['of.calculation.department']
        department = department_obj.search([('code', '=', zip[:2])], limit=1)
        if department:
            altitudes = department.base_temperature_id.line_ids.mapped('altitude_id')
            return altitudes.ids
