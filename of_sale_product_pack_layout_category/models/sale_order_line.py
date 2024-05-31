# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        node_id = 0
        for vals in vals_list:
            if line_id := vals.get('pack_parent_line_id'):
                sol = self.env['sale.order.line'].browse(line_id)
                if node_id == 0:
                    node_id = len(self.env['sale.order.line'].search([('order_id', '=', sol.order_id.id)])) + 1
                else:
                    node_id += 1
                vals['of_parent_node_id'] = sol.of_parent_node_id
                vals['of_node_id'] = node_id
        return super().create(vals_list)

    def write(self, vals):
        node_id = 0
        if line_id := vals.get('pack_parent_line_id'):
            sol = self.env['sale.order.line'].browse(line_id)
            if node_id == 0:
                node_id = len(self.env['sale.order.line'].search([('order_id', '=', sol.order_id.id)])) + 1
            else:
                node_id += 1
            vals['of_parent_node_id'] = sol.of_parent_node_id
            vals['of_node_id'] = node_id
        return super().write(vals)
