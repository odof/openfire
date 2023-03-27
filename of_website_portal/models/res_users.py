# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_cr_context
    def _auto_init(self):
        res = super(ResUsers, self)._auto_init()
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_website_portal'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.2.1.0' or False
        cr = self._cr
        if actions_todo:
            # On désactive les profils utilisateurs portail
            cr.execute("""
                UPDATE  res_users ru
                SET     active = FALSE
                FROM ir_model_data imd
                WHERE ru.id = imd.res_id
                AND imd.model = 'res.users'
                AND imd.module = 'of_website_portal'
                AND imd.name IN ('res_users_portal_b2b', 'res_users_portal_b2c'); """)
            # On attribue toutes les sociétés les profils utilisateurs portail
            cr.execute("""
                DELETE FROM res_company_users_rel
                WHERE       user_id IN (SELECT  imd.res_id
                                        FROM    ir_model_data imd
                                        WHERE   imd.model = 'res.users'
                                        AND     imd.module = 'of_website_portal'
                                        AND     imd.name IN ('res_users_portal_b2b', 'res_users_portal_b2c'));
                INSERT INTO res_company_users_rel (cid, user_id)
                SELECT      rc.id, ru.id
                FROM        res_users ru,
                            res_company rc,
                            ir_model_data imd
                WHERE       ru.id = imd.res_id
                AND         imd.model = 'res.users'
                AND         imd.module = 'of_website_portal'
                AND         imd.name IN ('res_users_portal_b2b', 'res_users_portal_b2c'); """)
            # On attribue des champs à mettre à jour pour les profils utilisateurs portail
            cr.execute("""
                DELETE FROM ir_model_fields_res_users_rel
                WHERE       res_users_id IN (   SELECT  imd.res_id
                                                FROM    ir_model_data imd
                                                WHERE   imd.model = 'res.users'
                                                AND     imd.module = 'of_website_portal'
                                                AND     imd.name IN ('res_users_portal_b2b', 'res_users_portal_b2c'));
                INSERT INTO ir_model_fields_res_users_rel (res_users_id, ir_model_fields_id)
                SELECT      ru.id, imf.id
                FROM        res_users ru,
                            ir_model_fields imf,
                            ir_model_data imd,
                            ir_model_data imd2
                WHERE       ru.id = imd.res_id
                AND         imd.model = 'res.users'
                AND         imd.module = 'of_website_portal'
                AND         imd.name IN ('res_users_portal_b2b', 'res_users_portal_b2c')
                AND         imf.id = imd2.res_id
                AND         imd2.model = 'ir.model.fields'
                AND         ((imd2.module = 'of_website_portal' AND imd2.name IN ('field_res_users_of_tab_ids', 'field_res_users_of_pricelist_id', 'field_res_users_of_fiscal_position_id'))
                OR          (imd2.module = 'base' AND imd2.name IN ('field_res_users_groups_id'))); """)
        # Ajouter les onglets RDV et CE pour tous les utilisateurs
        if module_self and module_self.latest_version < '10.0.2.2.0':
            cr.execute("""
            INSERT INTO res_users_of_tab_rel (user_id, tab_id)
            SELECT      ru.id, ot.id
            FROM        res_users ru,
                        of_tab ot,
                        ir_model_data imd
            WHERE       ot.id = imd.res_id
            AND         imd.model = 'of.tab'
            AND         imd.module = 'of_website_portal'
            AND         imd.name IN ('of_tab_intervention', 'of_tab_contract')
            ON CONFLICT DO NOTHING
            """)
        return res

    of_pricelist_id = fields.Many2one(comodel_name='product.pricelist', string=u"Liste de prix par défaut")
    of_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string=u"Position fiscale par défaut")
    of_tab_ids = fields.Many2many(
        comodel_name='of.tab', relation='res_users_of_tab_rel', column1='user_id', column2='tab_id', string="Onglets",
        default=lambda r: r._get_default_tab_ids())

    @api.model
    def _get_default_tab_ids(self):
        tabs = [
            self.env.ref('of_website_portal.of_tab_contract', raise_if_not_found=False),
            self.env.ref('of_website_portal.of_tab_intervention', raise_if_not_found=False),
        ]
        return [(4, tab.id) for tab in tabs if tab]

    @api.model
    def deactivate_portal_users(self):
        self.env.ref('of_website_portal.res_users_portal_b2b').active = False
        self.env.ref('of_website_portal.res_users_portal_b2c').active = False

    @api.model
    def create(self, vals):
        res = super(ResUsers, self).create(vals)
        if res.of_fiscal_position_id:
            res.partner_id.property_account_position_id = res.of_fiscal_position_id.id
        return res

    @api.multi
    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        for user in self:
            if user.of_fiscal_position_id:
                user.partner_id.property_account_position_id = user.of_fiscal_position_id.id
        return res


class OFTab(models.Model):
    _name = 'of.tab'
    _description = 'Onglet'
    _order = 'name asc'

    name = fields.Char(string="Nom", required=True)
    code = fields.Char(string="Code", required=True)
