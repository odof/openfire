# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def activate_of_analytique_code(self):
        ir_values_obj = self.env['ir.values']
        of_analytique_code = ir_values_obj.search(
            [('model', '=', 'sale.config.settings'), ('name', '=', 'of_analytique_code')], limit=1)
        if of_analytique_code:
            of_analytique_code.value_unpickle = "(partner.name, partner.ref)"
        else:
            ir_values_obj.sudo().set_default(
                'sale.config.settings', 'of_analytique_code', "(partner.name, partner.ref)")
