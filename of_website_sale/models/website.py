# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class Website(models.Model):
    _inherit = 'website'

    @api.model_cr_context
    def _auto_init(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_website_sale')])
        actions_todo = module_self and module_self.latest_version < '10.0.2' or False

        if actions_todo:
            website = self.env.ref('website.default_website')
            of_pricelist_b2c_id = website.of_pricelist_b2c_id.id
            of_pricelist_b2b_id = website.of_pricelist_b2b_id.id

            of_fiscal_position_b2c_id = website.of_fiscal_position_b2c_id.id
            of_fiscal_position_b2b_id = website.of_fiscal_position_b2b_id.id

        res = super(Website, self)._auto_init()

        if actions_todo:
            res_users_portal_b2b = self.env.ref('of_website_portal.res_users_portal_b2b')
            res_users_portal_b2c = self.env.ref('of_website_portal.res_users_portal_b2c')

            res_users_portal_b2c.of_pricelist_id = of_pricelist_b2c_id
            res_users_portal_b2b.of_pricelist_id = of_pricelist_b2b_id

            res_users_portal_b2c.of_fiscal_position_id = of_fiscal_position_b2c_id
            res_users_portal_b2b.of_fiscal_position_id = of_fiscal_position_b2b_id

        return res

    # Ne sont plus utilisés. Ne sont conservés que pour la migration des données qu'ils contiennent
    of_pricelist_b2c_id = fields.Many2one(comodel_name='product.pricelist', string='Liste de prix B2C')
    of_pricelist_b2b_id = fields.Many2one(comodel_name='product.pricelist', string='Liste de prix B2B')
    of_fiscal_position_b2c_id = fields.Many2one(comodel_name='account.fiscal.position', string='Position fiscale B2C')
    of_fiscal_position_b2b_id = fields.Many2one(comodel_name='account.fiscal.position', string='Position fiscale B2B')
