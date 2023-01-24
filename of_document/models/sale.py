# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_dms_file_count = fields.Integer(string="Documents", compute='_compute_of_dms_file_count')

    @api.multi
    def get_dms_file_domain(self):
        self.ensure_one()
        return [
            '|', '|', '&', ('of_related_model', '=', 'sale.order'), ('of_related_id', '=', self.id),
            '&', ('of_related_model', '=', 'account.invoice'), ('of_related_id', 'in', self.invoice_ids.ids),
            '&', ('of_related_model', '=', 'of.planning.intervention'),
            ('of_related_id', 'in', self.intervention_ids.ids)
        ]

    @api.multi
    def _compute_of_dms_file_count(self):
        for order in self:
            domain = order.get_dms_file_domain()
            order.of_dms_file_count = self.env['muk_dms.file'].search_count(domain)

    @api.multi
    def action_view_dms_files(self):
        self.ensure_one()
        action = self.env.ref('muk_dms.action_dms_file').read()[0]
        action['views'] = [
            (self.env.ref('muk_dms.view_dms_file_kanban').id, 'kanban'),
            (self.env.ref('muk_dms.view_dms_file_tree').id, 'tree'),
            (self.env.ref('muk_dms.view_dms_file_form').id, 'form')]
        action['domain'] = self.get_dms_file_domain()
        return action
