# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_intervention_ids = fields.One2many(
        comodel_name='calendar.event', inverse_name='of_order_id', string="Interventions"
    )
    of_intervention_count = fields.Integer(string="# Interventions", compute='_compute_of_intervention_count')
    of_intervention_notes = fields.Html(
        string="Intervention notes",
        help="These notes are visualized in the intervention planning and printed in the intervention form.",
    )
    of_is_fully_planned = fields.Boolean(string="Planned", compute='_compute_of_planned', store=True)

    @api.depends('of_intervention_ids')
    def _compute_of_intervention_count(self):
        for order in self:
            order.of_intervention_count = len(order.of_intervention_ids)

    @api.depends('order_line', 'order_line.of_intervention_state')
    def _compute_of_planned(self):
        for order in self:
            order.of_is_fully_planned = all(
                line.of_intervention_state in ['planned', 'done'] for line in order.order_line
            )

    def action_button_view_intervention(self):
        action = self.env.ref('of_planning.action_calendar_event').sudo().read()[0]
        if len(self._ids) == 1:
            picking_ids = self.picking_ids.ids
            context = safe_eval(action['context'])
            context.update(
                {
                    'default_of_partner_id': self.partner_id.id or False,
                    'default_of_address_id': self.partner_shipping_id.id or False,
                    'default_of_order_id': self.id,
                    'default_of_picking_manual_ids': [Command.set(picking_ids)],
                }
            )
            if self.of_intervention_ids:
                context['search_default_of_order_id'] = self.id
            action['context'] = context
            domain = safe_eval(action['domain']) if action.get('domain') else []
            domain += [('of_order_id', '=', self.id)]
            action['domain'] = domain
        action = self.mapped('of_intervention_ids')._get_calendar_event_action_views(action)
        return action

    def _get_report_sheet_base_filename(self):
        return _("Intervention Sheet - %s") % self.name
