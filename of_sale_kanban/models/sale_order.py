# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_kanban_stage_id = fields.Many2one(
        comodel_name="of.sale.order.kanban.stage",
        string="Étape de suivi",
        default=lambda s: s.env.ref("of_sale_kanban.of_sale_order_kanban_stage_new", raise_if_not_found=False),
        group_expand="_read_group_kanban_stage_ids",
        track_visibility="onchange",
    )

    @api.model
    def _read_group_kanban_stage_ids(self, stages, domain, order):
        kanban_step_ids = self.env["of.sale.order.kanban.stage"].search([])
        return kanban_step_ids
