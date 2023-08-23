# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFCalculationHeatLossHook(models.AbstractModel):
    _name = 'of.calculation.heat.loss.hook'

    @api.model
    def _update_version_10_0_1_1_0_hook(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_calculation_heat_loss'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version and module_self.latest_version < '10.0.1.1.0':
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            calculations = self.env['of.calculation.heat.loss'].search([])
            for calculation in calculations:
                calculation._onchange_order_id()
