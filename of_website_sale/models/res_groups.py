# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api

FIELDS_NAMES_SYNC_TRIGGER = ['view_access', 'rule_groups', 'model_access']
PORTAL_TO_B2C_FIELDS_LIST = ['name', 'model_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink']


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def write(self, values):

        if 'groups_id' in values:
            group_portal_b2c = self.env.ref('of_website_sale.group_portal_b2c')
            group_portal_b2b = self.env.ref('base.group_portal')

            for user in self:
                # On teste si on ajoute le groupe b2c sur l'utilisateur
                if group_portal_b2c.id == values['groups_id'][0][1] and values['groups_id'][0][0] == 4:

                    # On ajoute la liste de prix b2c ainsi que la position fiscale b2c
                    user.partner_id.property_product_pricelist = user.of_pricelist_id
                    user.partner_id.property_account_position_id = user.of_fiscal_position_id
                    # On supprime l'utilisateur du groupe b2b et des groupes impliqués
                    group_portal_b2b.users = [(3, user.id)]
                    for group in group_portal_b2b.implied_ids:
                        group.users = [(3, user.id)]

                # On teste si on ajoute le groupe b2b sur l'utilisateur
                if group_portal_b2b.id == values['groups_id'][0][1] and values['groups_id'][0][0] == 4:

                    # On ajoute la liste de prix b2b ainsi que la position fiscale b2c
                    user.partner_id.property_product_pricelist = user.of_pricelist_id
                    user.partner_id.property_account_position_id = user.of_fiscal_position_id
                    # On supprime l'utilisateur du groupe b2c et des groupes impliqués
                    group_portal_b2c.users = [(3, user.id)]
                    for group in group_portal_b2c.implied_ids:
                        group.users = [(3, user.id)]

        return super(ResUsers, self).write(values)


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def _auto_init_group_portal_b2c(self):
        """ Copy access rights, views and rules from group Portal to group Portal B2C
        """
        group_portal = self.env.ref('base.group_portal')
        group_portal_b2c = self.env.ref('of_website_sale.group_portal_b2c')
        model_access_obj = self.env['ir.model.access']

        b2c_model_accesses = model_access_obj.search([('group_id', '=', group_portal_b2c.id)])
        group_portal_b2c.view_access = group_portal.view_access
        group_portal_b2c.rule_groups = group_portal.rule_groups

        for portal_model_access in group_portal.model_access:
            ma_attr_list = [portal_model_access[field] for field in PORTAL_TO_B2C_FIELDS_LIST]
            equivalent_rule = b2c_model_accesses.filtered(
                lambda ma: [ma[field] for field in PORTAL_TO_B2C_FIELDS_LIST] == ma_attr_list)
            if not equivalent_rule:
                # Copy values from group Portal to group Portal B2C
                portal_model_access.copy({
                    'group_id': group_portal_b2c.id,
                })

        return True

    @api.multi
    def write(self, values):
        res = super(ResGroups, self).write(values)
        group_portal = self.env.ref('base.group_portal')
        if group_portal in self and any(field in values for field in FIELDS_NAMES_SYNC_TRIGGER):
            self.env['res.groups']._auto_init_group_portal_b2c()
        return res
