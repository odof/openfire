# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields


class OFSaleQuoteTemplateActivity(models.Model):
    _name = 'of.sale.quote.tmpl.activity'
    _description = 'OF Sale Quote Template Activity'
    _order = 'sequence'

    template_id = fields.Many2one(
        comodel_name='sale.quote.template', string='Template', index=True, required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=1)
    activity_id = fields.Many2one(
        comodel_name='crm.activity', string='Activity type', index=True, required=True,
        domain=['|', ('of_object', '=', 'sale_order'), ('of_object', '=', False)])
    description = fields.Text(string='Description')
    compute_date = fields.Selection(selection='_get_compute_date_selection', string='Compute Date')
    days = fields.Integer(string='Delay')

    @api.model
    def _get_compute_date_selection(self):
        return self.env['crm.activity']._get_of_compute_date_selection_sale()

    @api.multi
    def _get_sale_activity_values(self, order):
        self.ensure_one()
        order_obj = self.env['sale.order']
        date_deadline = order_obj._of_get_sale_activity_date_deadline(
            order, self.activity_id, self.days, self.compute_date)
        user_id = order_obj._of_get_sale_activity_user_id(order, self.activity_id)
        trigger_type = self.activity_id.of_trigger_type
        active = trigger_type in [False, 'at_creation']
        return {
            'type_id': self.activity_id.id,
            'description': self.description,
            'deadline_date': date_deadline,
            'title': self.activity_id.of_short_name,
            'state': 'planned',
            'sequence': self.sequence,
            'vendor_id': user_id,
            'user_id': self.env.user.id,
            'load_attachment': self.activity_id.of_load_attachment,
            'order_id': order.id,
            'origin': 'sale_order',
            'trigger_type': trigger_type,
            'active': active
        }

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if self.activity_id:
            self.description = self.activity_id.description
            self.compute_date = self.activity_id.of_compute_date
            self.days = self.activity_id.days
