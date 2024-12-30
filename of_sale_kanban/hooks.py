# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    orders = env["sale.order"].search([])
    if default_stage := env.ref("of_sale_kanban.of_sale_order_kanban_stage_new", raise_if_not_found=False):
        orders.write({"of_kanban_stage_id": default_stage.id})
