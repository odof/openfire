# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_dms_file_count = fields.Integer(string="Documents", compute='_compute_dms_file')

    @api.multi
    def _compute_dms_file(self):
        for order in self:
            order.of_dms_file_count = self.env['muk_dms.file'].search_count(
                [('of_related_model', '=', 'sale.order'), ('of_related_id', '=', order.id)])

    @api.multi
    def action_view_dms_files(self):
        self.ensure_one()
        if self.of_dms_file_count:
            order_files = self.env['muk_dms.file'].search(
                [('of_related_model', '=', 'sale.order'), ('of_related_id', '=', self.id)])
            action = self.env.ref('muk_dms.action_dms_file').read()[0]
            action['views'] = [
                (self.env.ref('muk_dms.view_dms_file_kanban').id, 'kanban'),
                (self.env.ref('muk_dms.view_dms_file_tree').id, 'tree'),
                (self.env.ref('muk_dms.view_dms_file_form').id, 'form')]
            action['domain'] = [('id', 'in', order_files.ids)]
            return action
