# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        create_portal_users = self.env['ir.values'].get_default('base.config.settings', 'of_create_portal_users')
        if create_portal_users == 'contact_creation':
            res._create_portal_user()
        return res

    @api.multi
    def _create_portal_user(self):
        res_users_obj = self.env['res.users']
        portal_wizard_obj = self.env['portal.wizard']
        portal = self.env['res.groups'].search([('is_portal', '=', True)], limit=1)
        user_profile_id = self.env.ref('of_website_portal.res_users_portal_b2c', raise_if_not_found=False)
        if not user_profile_id:
            user_profile_id = self.env.ref('of_website_portal.res_users_portal_b2b', raise_if_not_found=False)
        if not user_profile_id:
            user_profile_id = res_users_obj.with_context(active_test=False).search([
                ('groups_id', 'in', portal.ids), ('of_is_user_profile', '=', True)], limit=1)

        if user_profile_id:
            users = []
            for partner in self:
                if partner.email and partner.company_id and not partner.user_ids:
                    users.append((0, 0, {
                        'partner_id': partner.id,
                        'email': partner.email,
                        'in_portal': True,
                        'of_user_profile_id': user_profile_id.id,
                        'active': True,
                    }))
            if users:
                portal_wizard = portal_wizard_obj.create({
                    'portal_id': portal.id,
                    'user_ids': users,
                })
                portal_wizard.onchange_portal_id()
                portal_wizard.action_apply()


