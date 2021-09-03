# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class ResGroups(models.Model):
    _inherit = 'res.groups'

    # On récupère tous les droits/vues/règles du groupe Portail pour les mettre sur Portail B2C
    @api.model
    def _auto_init_group_portal_b2c(self):
        group_portal = self.env.ref('base.group_portal')
        group_portal_b2c = self.env.ref('of_website_portal.group_portal_b2c')

        group_portal_b2c.view_access = group_portal.view_access
        group_portal_b2c.rule_groups = group_portal.rule_groups

        for model_access in group_portal.model_access:
            model_access.copy({
                'group_id': group_portal_b2c.id,
            })

        return True
