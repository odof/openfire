# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def update_group_of_project_issue_not_migrated(self):
        # On utilise une fonction déclenchée par le XML plutôt qu'un auto_init,
        # car au moment de l'auto_init, le groupe n'existe pas encore
        # Si la migration n'a pas été faite, ajouter le groupe project_issue_not_migrated à tous les utilisateurs
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            group_not_migrated = self.env.ref('of_service_parc_installe.group_of_project_issue_not_migrated')
            users_add = self.sudo().with_context(active_test=False).search(
                [('groups_id', 'not in', group_not_migrated.id)])
            users_add.write({'groups_id': [(4, group_not_migrated.id)]})

    @api.model
    def create(self, vals):
        # Si la migration n'a pas été faite, ajouter le groupe project_issue_not_migrated
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            group_not_migrated = self.env.ref('of_service_parc_installe.group_of_project_issue_not_migrated')
            groups_id = vals.get('groups_id', [])
            groups_id.append((4, group_not_migrated.id))
            vals['groups_id'] = groups_id
        return super(ResUsers, self).create(vals)
