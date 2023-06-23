# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

from odoo.addons.of_utils.models.of_utils import get_selection_label


class OFCRMActivity(models.Model):
    _inherit = 'of.crm.activity'

    order_id = fields.Many2one(comodel_name='sale.order', string="Sale Order", ondelete='cascade')
    trigger_type = fields.Selection(
        selection=[('at_creation', "At creation"), ('at_validation', "At validation")], string="Trigger"
    )

    @api.model
    def _get_selection_origin(self):
        return super()._get_selection_origin() + [('sale_order', _('Sale Order'))]

    @api.depends('origin', 'order_id', 'opportunity_id', 'order_id.partner_id', 'opportunity_id.partner_id')
    def _compute_partner_id(self):
        order_activities = self.filtered(lambda a: a.origin == 'sale_order')
        for activity in order_activities:
            activity.partner_id = activity.order_id.partner_id
        super(OFCRMActivity, self - order_activities)._compute_partner_id()

    def _compute_is_late(self):
        order_activities = self.filtered(lambda a: a.origin == 'sale_order')
        if order_activities:
            today = fields.Date.today()
            for activity in self:
                activity.state == 'planned' and activity.deadline_date < today if activity.deadline_date else False
        super(OFCRMActivity, self - order_activities)._compute_is_late()

    @api.model
    def get_is_late_domain(self):
        return expression.OR(
            (
                ['&', ('origin', '=', 'sale_order'), ('deadline_date', '<', fields.Date.today())],
                super().get_is_late_domain(),
            )
        )

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            if self.origin == 'sale_order':
                user = self.order_id._of_get_sale_activity_user(self.type_id)
                if user:
                    self.vendor_id = user
                self.deadline_date = self.order_id._of_get_sale_activity_date_deadline(self.type_id)
                self.trigger_type = self.type_id.of_trigger_type
            else:
                self.trigger_type = False
        return super()._onchange_type_id()

    @api.multi
    def action_complete(self):
        current_states = {rec: get_selection_label(self, rec._name, 'state', rec.state) for rec in self}
        for rec in self:
            if rec.load_attachment and rec.type_id.of_mandatory and not rec.uploaded_attachment_id:
                raise ValidationError(_('An attachment is required to complete the activity'))
        self.write({'state': 'done', 'done_date': fields.Datetime.now()})
        self._post_order_message_status(current_states)
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def action_cancel(self):
        current_states = {rec: get_selection_label(self, rec._name, 'state', rec.state) for rec in self}
        self.write({'state': 'canceled', 'active': False})
        self._post_order_message_status(current_states)
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def _post_order_message_status(self, current_states):
        for rec in self:
            if rec.order_id:
                to_state = get_selection_label(self, rec._name, 'state', rec.state)
                rec.order_id.message_post(
                    body=_("Activity status change %s : %s -> %s") % (rec.title, current_states[rec], to_state)
                )

    @api.multi
    def action_add_attachment(self):
        self.ensure_one()
        context = self._context.copy()
        context['default_activity_id'] = self.id
        if self.origin == 'opportunity':
            context['default_lead_id'] = self.opportunity_id.id
        else:
            context['default_order_id'] = self.order_id.id
        view_id = self.env.ref('of_crm.of_add_attachment_activity_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'of.add.attachment.activity',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': context,
        }
