# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.addons.of_utils.models.of_utils import get_selection_label


class OFSaleActivity(models.Model):
    _name = 'of.sale.activity'
    _description = 'OF Sale Activity'
    _rec_name = 'summary'
    _order = "sequence, summary"

    sequence = fields.Integer(string='Sequence', default=1)
    order_id = fields.Many2one(
        comodel_name='sale.order', string='Sale Order', required=True, index=True, ondelete='cascade')
    activity_id = fields.Many2one(
        comodel_name='crm.activity', string='Activity type', required=True, index=True,
        domain=['|', ('of_object', '=', 'sale_order'), ('of_object', '=', False)])
    summary = fields.Char(string='Summary', required=True)
    date_deadline = fields.Date(string='Deadline date')
    description = fields.Text(string='Description')
    report = fields.Text(string='Report')
    state = fields.Selection(selection=[
        ('planned', 'Planned'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')], string='State', index=True, required=True, default='planned')
    is_overdue = fields.Boolean(string='Is overdue activity ?', compute='_compute_is_overdue')
    load_attachment = fields.Boolean(string='Load an attachment')
    uploaded_attachment_id = fields.Many2one(comodel_name='ir.attachment', string='Uploaded attachment')
    user_id = fields.Many2one(comodel_name='res.users', string='Assigned to', index=True)

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if self.activity_id:
            order_obj = self.env['sale.order']
            self.date_deadline = order_obj._of_get_sale_activity_date_deadline(
                self.order_id, self.activity_id)
            self.description = self.activity_id.description
            self.summary = self.activity_id.of_short_name
            self.load_attachment = self.activity_id.of_load_attachment
            user_id = order_obj._of_get_sale_activity_user_id(self.order_id, self.activity_id)
            if user_id:
                self.user_id = user_id

    @api.multi
    def _compute_is_overdue(self):
        today = fields.Date.from_string(fields.Date.today())
        for rec in self:
            rec.is_overdue = rec.state == 'planned' and fields.Date.from_string(rec.date_deadline) < today \
                if rec.date_deadline else False

    @api.multi
    def _post_order_message_status(self, current_states):
        for rec in self:
            if rec.order_id:
                to_state = get_selection_label(self, rec._name, 'state', rec.state)
                rec.order_id.message_post(
                    body=_("Activity status change %s : %s -> %s") % (rec.summary, current_states[rec], to_state))

    @api.multi
    def action_plan(self):
        self.write({'state': 'planned'})
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def action_complete(self):
        current_states = {rec: get_selection_label(self, rec._name, 'state', rec.state) for rec in self}
        for rec in self:
            if self.load_attachment and rec.activity_id.of_mandatory and not rec.uploaded_attachment_id:
                raise ValidationError(_('An attachment is required to complete the activity'))
        self.write({'state': 'done'})
        self._post_order_message_status(current_states)
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def action_cancel(self):
        current_states = {rec: get_selection_label(self, rec._name, 'state', rec.state) for rec in self}
        self.write({'state': 'cancelled'})
        self._post_order_message_status(current_states)
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def action_add_attachment(self):
        self.ensure_one()
        context = self._context.copy()
        context.update({
            'default_order_id': self.order_id.id,
            'default_sale_activity_id': self.id
        })
        view_id = self.env.ref(
            'of_crm.of_add_attachment_activity_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'of.add.attachment.activity',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': context
        }
