# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models
from odoo.tools.safe_eval import safe_eval


class StockPicking(models.Model):
    _inherit = "stock.picking"

    of_intervention_ids = fields.Many2many(
        comodel_name="calendar.event",
        string="Linked interventions",
        relation="of_calendar_event_picking_manual_rel",
        column1="picking_id",
        column2="intervention_id",
        compute="_compute_of_intervention_ids",
    )
    of_intervention_count = fields.Integer(string="# linked Interventions", compute="_compute_of_intervention_ids")

    def _compute_of_intervention_ids(self):
        event_obj = self.env["calendar.event"]
        for picking in self:
            interventions = event_obj.search([("of_picking_manual_ids", "=", picking.id)])
            picking.of_intervention_ids = interventions
            picking.of_intervention_count = len(interventions)

    def action_button_view_interventions(self):
        events = self.mapped("of_intervention_ids")
        action = self.env.ref("of_planning.action_calendar_event").sudo().read()[0]
        if len(self.ids) == 1:
            context = safe_eval(action["context"])
            orders = self.mapped("sale_id")
            context.update(
                {
                    "default_of_address_id": self.partner_id.id or False,
                    "default_of_picking_manual_ids": [Command.set(self.ids)],
                    "default_of_order_id": orders and orders[0].id or False,
                }
            )
            action["context"] = context
            action["domain"] = [("of_picking_manual_ids", "in", self.ids)]
            if len(events) == 1:
                action["res_id"] = events[0].id
        action = events._get_calendar_event_action_views(action)
        return action

    def action_button_open_picking_manual(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": self.id,
            "view_mode": "form",
        }
