# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class PortalWizardUser(models.TransientModel):
    _inherit = 'portal.wizard.user'

    of_user_profile_id = fields.Many2one(
        comodel_name='res.users', string=u"Profil utilisateur", context={'active_test': False})

    user_group_ids = fields.Many2many(
        comodel_name='res.users', relation='portal_wizard_res_users_rel', column1='wizard_id',
        column2='user_id', string=u"Utilisateurs ayant le groupe", compute='_compute_user_group_ids')

    @api.onchange('of_user_profile_id')
    def _onchange_of_user_profile_id(self):
        self.in_portal = self.of_user_profile_id and True or False

    @api.depends('wizard_id.portal_id')
    def _compute_user_group_ids(self):
        res_users_obj = self.env['res.users']
        for user in self:
            user.user_group_ids = [
                (6, 0, res_users_obj.search([('groups_id', 'in', user.wizard_id.portal_id.ids)]).ids)]

    @api.multi
    def action_apply(self):
        res = super(PortalWizardUser, self).action_apply()

        for wizard_user in self.sudo().with_context(active_test=False):
            user = self.env['res.users'].search([('partner_id', '=', wizard_user.partner_id.id)], limit=1)
            if user:
                user.of_user_profile_id = wizard_user.of_user_profile_id.id

        return res
