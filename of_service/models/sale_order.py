# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_request_ids = fields.One2many(
        comodel_name='of.service.request',
        inverse_name='order_id',
        string="Service Requests",
        copy=False,
        store=True,
    )
    of_request_count = fields.Integer(string="Service Requests", compute='_compute_of_request_count')

    @api.depends('of_request_ids', 'order_line.of_request_line_id')
    def _compute_of_request_count(self):
        for order in self:
            requests = order.of_request_ids.filtered(lambda s: s.state != 'cancel')
            requests |= order.mapped('order_line.of_request_line_id.request_id')
            order.of_request_ids = requests
            order.of_request_count = len(requests)

    def action_button_view_request(self):
        self.ensure_one()
        return self._get_action_view_request(self.of_request_ids)

    def _get_action_view_request(self, requests):
        """Return an action to display the service requests linked to the sale order"""
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('of_service.action_of_service_request')
        date_today = fields.Datetime.now()
        fortnight_date = date_today + timedelta(days=14)  # arbitrary date in the future, 2 weeks from now
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_address_id': self.partner_shipping_id.id or self.partner_id.id,
            'default_recurrency': False,
            'default_next_date': date_today,
            'default_stop_date': fortnight_date,
            'default_origin': _("[Order] %s") % self.name,
            'default_order_id': self.id,
            'default_type_id': self.env.ref('of_service.of_service_request_type_installation').id,
        }
        # Choose the view_mode accordingly
        if not requests or len(requests) > 1:
            action['domain'] = [('id', 'in', requests.ids)]
        elif len(requests) == 1:
            form_view = self.env.ref('of_service.of_service_request_view_form', raise_if_not_found=False)
            # Put the form view in first position
            action['views'] = [(form_view and form_view.id or False, 'form')] + [
                (state, view) for state, view in action.get('views', []) if view != 'form'
            ]
            action['res_id'] = requests.id
        return action

    def action_button_schedule_intervention(self):
        self.ensure_one()
        date_today = fields.Datetime.now()
        fortnight_date = date_today + timedelta(days=14)  # arbitrary date in the future, 2 weeks from now
        return {
            'type': 'ir.actions.act_window',
            'name': _("Schedule an intervention"),
            'res_model': 'of.service.request',
            'view_mode': 'form',
            'view_id': self.env.ref('of_service.of_service_request_view_form').id,
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_address_id': self.partner_shipping_id.id or self.partner_id.id,
                'default_recurrency': False,
                'default_next_date': date_today,
                'default_stop_date': fortnight_date,
                'default_origin': _("[Order] %s") % self.name,
                'default_order_id': self.id,
                'hide_schedule_button': True,
                'default_type_id': self.env.ref('of_service.of_service_request_type_installation').id,
            },
        }
