# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_kanban_stage_id = fields.Many2one(
        comodel_name="of.sale.order.kanban.stage",
        string="Tracking stage",
        default=lambda s: s.env.ref("of_sale_kanban.of_sale_order_kanban_stage_new", raise_if_not_found=False),
        group_expand="_read_group_kanban_stage_ids",
        tracking=True,
    )
    of_main_product_name = fields.Char(string="Main product name", compute="_compute_main_product_name", store=True)

    @api.depends("order_line.of_main_product")
    def _compute_main_product_name(self):
        for order in self:
            if main_product := order.order_line.filtered(lambda line: line.of_main_product):
                order.of_main_product_name = main_product[:1].product_id.name

    @api.model
    def _read_group_kanban_stage_ids(self, stages, domain, order):
        return self.env["of.sale.order.kanban.stage"].search([])
