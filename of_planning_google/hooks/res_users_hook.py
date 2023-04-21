# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _init_of_google_company_id(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_planning_google')])

        if not module_self.latest_version or module_self.latest_version < '10.0.1.0.1':
            cr = self.env.cr
            cr.execute("UPDATE res_users SET of_google_company_id = company_id")
