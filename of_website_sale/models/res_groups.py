# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def write(self, values):

        if 'groups_id' in values:
            group_portal_b2c = self.env.ref('of_website_sale.group_portal_b2c')
            group_portal_b2b = self.env.ref('base.group_portal')
            website_id = self.env.ref('website.default_website')

            for user in self:
                # On teste si on ajoute le groupe b2c sur l'utilisateur
                if group_portal_b2c.id == values['groups_id'][0][1] and values['groups_id'][0][0] == 4:

                    # On ajoute la liste de prix b2c ainsi que la position fiscale b2c
                    user.partner_id.property_product_pricelist = website_id.of_pricelist_b2c_id
                    user.partner_id.property_account_position_id = website_id.of_fiscal_position_b2c_id
                    # On supprime l'utilisateur du groupe b2b et des groupes impliqués
                    group_portal_b2b.users = [(3, user.id)]
                    for group in group_portal_b2b.implied_ids:
                        group.users = [(3, user.id)]

                # On teste si on ajoute le groupe b2b sur l'utilisateur
                if group_portal_b2b.id == values['groups_id'][0][1] and values['groups_id'][0][0] == 4:

                    # On ajoute la liste de prix b2b ainsi que la position fiscale b2c
                    user.partner_id.property_product_pricelist = website_id.of_pricelist_b2b_id
                    user.partner_id.property_account_position_id = website_id.of_fiscal_position_b2b_id
                    # On supprime l'utilisateur du groupe b2c et des groupes impliqués
                    group_portal_b2c.users = [(3, user.id)]
                    for group in group_portal_b2c.implied_ids:
                        group.users = [(3, user.id)]

        return super(ResUsers, self).write(values)


class ResGroups(models.Model):
    _inherit = 'res.groups'

    # On récupère tous les droits/vues/règles du groupe Portail pour les mettre sur Portail B2C
    @api.model
    def _auto_init_group_portal_b2c(self):
        group_portal = self.env.ref('base.group_portal')
        group_portal_b2c = self.env.ref('of_website_sale.group_portal_b2c')

        group_portal_b2c.view_access = group_portal.view_access
        group_portal_b2c.rule_groups = group_portal.rule_groups

        for model_access in group_portal.model_access:
            model_access.copy({
                'group_id': group_portal_b2c.id,
            })

        return True
