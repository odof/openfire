# -*- coding: utf8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_tasks_values(self):
        self.ensure_one()
        values = []
        for line in self.order_line:
            product = line.product_id
            description = line.name if product.type == 'service' else ''
            for task in product.of_product_tasks_tmpl_ids:
                nbr_hour = task.duration * line.product_uom_qty
                values.append({
                    'name': task.name,
                    'planned_hours': nbr_hour,
                    'remaining_hours': nbr_hour,
                    'partner_id': self.partner_id.id,
                    'user_id': False,
                    'description': description,
                    'sale_line_id': line.id,
                    'of_planning_tache_id': task.planning_tache_id.id,
                    'user_id': task.user_id.id,
                })
        return values

    def _prepare_project_vals(self):
        vals = super(SaleOrder, self)._prepare_project_vals()
        vals['tasks'] = [(0, 0, task) for task in self._prepare_tasks_values()]
        return vals

    @api.multi
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        project_obj = self.env['project.project']
        for rec in self:
            tasks = rec.order_line.mapped('product_id.of_product_tasks_tmpl_ids')
            if tasks:
                project_obj.create(rec._prepare_project_vals())
        return result
