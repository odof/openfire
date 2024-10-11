# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_intervention_line_ids = fields.One2many(
        comodel_name="of.planning.intervention.line", inverse_name="order_line_id"
    )
    of_qty_planning_done = fields.Float(
        string="Qty done",
        compute="_compute_of_qty_planning_done",
        store=True,
        digits="Product Unit of Measure",
        compute_sudo=True,
    )
    of_intervention_state = fields.Selection(
        selection=[
            ("todo", "To plan"),
            ("planned", "Planned"),
            ("done", "Done"),
        ],
        string="Planning status",
        compute="_compute_intervention_state",
        store=True,
        compute_sudo=True,
    )

    @api.depends(
        "of_intervention_line_ids", "of_intervention_line_ids.qty", "of_intervention_line_ids.intervention_state"
    )
    def _compute_of_qty_planning_done(self):
        for line in self:
            lines = line.of_intervention_line_ids.filtered(lambda li: li.intervention_state in ["done"])
            line.of_qty_planning_done = sum(lines.mapped("qty"))

    @api.depends("of_intervention_line_ids", "of_intervention_line_ids.intervention_state")
    def _compute_intervention_state(self):
        for line in self:
            state_done = [state == "done" for state in line.of_intervention_line_ids.mapped("intervention_state")]
            state_confirm = [
                state in ["draft", "confirmed", "done"]
                for state in line.of_intervention_line_ids.mapped("intervention_state")
            ]
            if state_done and all(state_done):
                line.of_intervention_state = "done"
            elif state_confirm and all(state_confirm):
                line.of_intervention_state = "planned"
            else:
                line.of_intervention_state = "todo"

    @api.model_create_multi
    def create(self, vals_list):
        order_obj = self.env["sale.order"]
        for vals in vals_list:
            if vals.get("order_id", False):
                order = order_obj.browse(vals["order_id"])
                if order and order.state == "sale":
                    # Force move date to the picking scheduled date if we are creating a move
                    # from a confirmed sale order
                    self = self.with_context(of_create_line_from_confirmed_sale=True)
        return super(SaleOrderLine, self).create(vals_list)
