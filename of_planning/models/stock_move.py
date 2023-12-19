# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        if self._context.get('of_create_line_from_confirmed_sale', False) and vals.get('picking_id', False):
            # Force move date to the picking scheduled date if we are creating a move from a confirmed sale order
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking and picking.of_intervention_ids:
                vals['date'] = picking.scheduled_date
        return super().write(vals)

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder)
        self._update_intervention_delivered_quantity()
        return res

    def _update_intervention_delivered_quantity(self):
        """Update the delivered quantity on the intervention lines."""
        intervention_lines = self.filtered(lambda move: move.product_id.expense_policy == 'no').mapped(
            'group_id.of_intervention_id.of_line_ids'
        )
        for line in intervention_lines:
            line.qty_delivered = line._get_delivered_qty()

    def _get_new_picking_values(self):
        res = super()._get_new_picking_values()
        interventions = self.mapped('group_id.of_intervention_id')
        if len(interventions) == 1:
            res['scheduled_date'] = interventions.start.date()
        return res
