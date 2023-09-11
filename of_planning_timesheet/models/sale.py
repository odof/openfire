# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def activate_of_analytique_code(self):
        # On crée un compte analytique par défaut par société
        res_company_obj = self.env['res.company']
        analytic_account_obj = self.env['account.analytic.account']
        for company in res_company_obj.search([]):
            analytic_account = analytic_account_obj.create({
                'name': u"Compte analytique par défaut - %s" % company.name,
                'company_id': company.id,
            })
            company.of_account_id = analytic_account.id

        # On active la compta analytique
        ir_values_obj = self.env['ir.values']
        analytique_code_value = ir_values_obj.search(
            [('model', '=', 'sale.config.settings'), ('name', '=', 'of_analytique_code')], limit=1)
        if analytique_code_value:
            analytique_code_value.value_unpickle = "(partner.name, partner.ref)"
        else:
            ir_values_obj.sudo().set_default(
                'sale.config.settings', 'of_analytique_code', "(partner.name, partner.ref)")
