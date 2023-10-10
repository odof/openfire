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

    @api.model
    def _update_version_10_0_3(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_calculation_heat_loss'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.3'
        if actions_todo:
            cr = self._cr
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1863.6
                WHERE   code = 1;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1977.3
                WHERE   code = 2;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1879.65
                WHERE   code = 3;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1613.45
                WHERE   code = 4;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2025.95
                WHERE   code = 5;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 896.65
                WHERE   code = 6;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1523.5
                WHERE   code = 7;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2196.55
                WHERE   code = 8;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1554.25
                WHERE   code = 9;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1933.2
                WHERE   code = 10;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1272.05
                WHERE   code = 11;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1892.4
                WHERE   code = 12;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1079.9
                WHERE   code = 13;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1796.7
                WHERE   code = 14;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2024.5
                WHERE   code = 15;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1369.7
                WHERE   code = 16;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1350.45
                WHERE   code = 17;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1708.2
                WHERE   code = 18;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1490.1
                WHERE   code = 19;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 935.95
                WHERE   code = 20;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1948.8
                WHERE   code = 21;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1676.3
                WHERE   code = 22;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1926.45
                WHERE   code = 23;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1510.3
                WHERE   code = 24;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1895.65
                WHERE   code = 25;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1445.7
                WHERE   code = 26;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1878.7
                WHERE   code = 27;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1851.65
                WHERE   code = 28;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1591.05
                WHERE   code = 29;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1173.3
                WHERE   code = 30;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1317.5
                WHERE   code = 31;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1402.7
                WHERE   code = 32;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1231.0
                WHERE   code = 33;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1159.2
                WHERE   code = 34;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1561.9
                WHERE   code = 35;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1781.05
                WHERE   code = 36;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1640.7
                WHERE   code = 37;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1999.75
                WHERE   code = 38;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1822.25
                WHERE   code = 39;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1318.4
                WHERE   code = 40;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1796.7
                WHERE   code = 41;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1925.0
                WHERE   code = 42;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2377.4
                WHERE   code = 43;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1472.9
                WHERE   code = 44;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1821.55
                WHERE   code = 45;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1514.5
                WHERE   code = 46;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1379.35
                WHERE   code = 47;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2207.45
                WHERE   code = 48;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1532.75
                WHERE   code = 49;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1693.8
                WHERE   code = 50;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1953.3
                WHERE   code = 51;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2154.55
                WHERE   code = 52;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1730.55
                WHERE   code = 53;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2036.3
                WHERE   code = 54;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2097.95
                WHERE   code = 55;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1585.95
                WHERE   code = 56;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2015.0
                WHERE   code = 57;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1901.05
                WHERE   code = 58;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1860.4
                WHERE   code = 59;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1999.25
                WHERE   code = 60;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1836.9
                WHERE   code = 61;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1801.5
                WHERE   code = 62;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1709.25
                WHERE   code = 63;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1290.25
                WHERE   code = 64;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1493.75
                WHERE   code = 65;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 959.85
                WHERE   code = 66;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1916.15
                WHERE   code = 67;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1998.8
                WHERE   code = 68;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1683.05
                WHERE   code = 69;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2099.35
                WHERE   code = 70;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1748.25
                WHERE   code = 71;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1604.0
                WHERE   code = 72;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2131.45
                WHERE   code = 73;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1988.5
                WHERE   code = 74;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1549.8
                WHERE   code = 75;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1962.7
                WHERE   code = 76;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1815.6
                WHERE   code = 77;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1837.45
                WHERE   code = 78;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1515.6
                WHERE   code = 79;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1898.3
                WHERE   code = 80;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1461.7
                WHERE   code = 81;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1433.25
                WHERE   code = 82;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1178.3
                WHERE   code = 83;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1387.45
                WHERE   code = 84;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1571.6
                WHERE   code = 85;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1644.7
                WHERE   code = 86;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1704.5
                WHERE   code = 87;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2155.65
                WHERE   code = 88;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1888.85
                WHERE   code = 89;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 2050.05
                WHERE   code = 90;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1697.8
                WHERE   code = 91;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1595.55
                WHERE   code = 92;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1704.85
                WHERE   code = 93;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1595.55
                WHERE   code = 94;""")
            cr.execute("""
                UPDATE  of_calculation_department
                SET     unified_day_degree = 1732.25
                WHERE   code = 95;""")
