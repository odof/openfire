# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _init_group_of_can_modify_sale_price_unit(cr):
    cr.execute(
        """
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT  imd.res_id, rgur.uid
        FROM    res_groups_users_rel rgur,
                ir_model_data imd
        WHERE   imd.model = 'res.groups'
        AND     imd.module = 'of_sale_no_discount'
        AND     imd.name IN ('group_of_can_modify_sale_price_unit')
        AND     rgur.gid = (SELECT 	imd2.res_id
                            FROM    ir_model_data imd2
                            WHERE   imd2.model = 'res.groups'
                            AND     imd2.module = 'base'
                            AND     imd2.name IN ('group_user'))
        ON CONFLICT DO NOTHING;"""
    )


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _init_group_of_can_modify_sale_price_unit(env.cr)
