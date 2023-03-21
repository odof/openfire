# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFCalculationHeatLoss(models.Model):
    _inherit = 'of.calculation.heat.loss'

    @api.model
    def of_calculation_heat_loss_demo(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.calculation.heat.loss'
        }
