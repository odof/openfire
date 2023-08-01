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

    @api.model
    def _update_version_10_0_2(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_calculation_heat_loss'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.2'
        if actions_todo:
            cr = self._cr
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     coefficient = 0.6,
                        message = 'Une étude thermique réglementaire réalisée par un bureau d''étude est impérative à la réception des travaux. Il s''agit ici d''une estimation.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_2').id)
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     coefficient = 0.8,
                        message = 'Calcul effectué en bureau d''étude. Il s''agit ici d''une estimation.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_3').id)
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     coefficient = 0.9,
                        message = 'Calcul effectué en bureau d''étude. Il s''agit ici d''une estimation.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_4').id)
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     message = 'Basé sur la méthode de calcul du G instaurée par la RT 1974.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_5').id)
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     message = 'Basé sur la méthode de calcul du G instaurée par la RT 1974.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_6').id)
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     message = 'Basé sur la méthode de calcul du G instaurée par la RT 1974.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_7').id)
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     message = 'Basé sur la méthode de calcul du G instaurée par la RT 1974.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_8').id)
            cr.execute("""
                UPDATE  of_calculation_construction_date
                SET     message = 'Basé sur la méthode de calcul du G instaurée par la RT 1974.'
                WHERE   id = %s;""" % self.env.ref('of_calculation_heat_loss.construction_date_9').id)
