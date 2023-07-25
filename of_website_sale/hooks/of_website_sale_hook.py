# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class OFWebsiteSaleHook(models.AbstractModel):
    _name = 'of.website.sale.hook'

    def _unlink_group_portal_b2c_model_accesses(self):
        """ Suppression des ir.model.access qui ont été créées plusieurs fois """
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_website_sale'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.2.1.1' or False
        if actions_todo:
            group_portal_b2c = self.env.ref('of_website_sale.group_portal_b2c')
            group_portal = self.env.ref('base.group_portal')
            cr = self._cr
            # On supprime tous les ir.model.access du groupe Portail B2C pour supprimer les doublons,
            # puis on les recréer à partir de ceux du groupe Portail
            cr.execute("""
                DELETE FROM ir_model_access
                WHERE group_id = %i;
                """ % group_portal_b2c.id)
            cr.execute("""
                INSERT INTO ir_model_access (
                    active, name, model_id, group_id, perm_read, perm_write, perm_create, perm_unlink)
                (SELECT active, name, model_id, %i, perm_read, perm_write, perm_create, perm_unlink
                FROM ir_model_access
                WHERE  group_id = %i);
                """ % (group_portal_b2c.id, group_portal.id))
