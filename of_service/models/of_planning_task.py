# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class OFPlanningTask(models.Model):
    _inherit = "of.planning.task"

    request_ids = fields.One2many(comodel_name="of.service.request", inverse_name="task_id", string="Service requests")
    request_count = fields.Integer(compute="_compute_request_count")

    is_recurring = fields.Boolean(string="Recurring Task")
    recurring_rule_type = fields.Selection(
        selection=[("monthly", "Monthly"), ("yearly", "Yearly")],
        string="Recurring Rule",
        default="yearly",
        help="Specify the interval for automatic calculation of the next planning date in recurring tasks.",
    )
    recurring_interval = fields.Integer(string="Repeat every", default=1, help="Repeat (Months/Years)")
    recurrency_display = fields.Char(string="Recurrency", compute="_compute_recurrency_display")

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("request_ids")
    def _compute_request_count(self):
        for task in self:
            task.request_count = len(task.request_ids)

    @api.depends("is_recurring", "recurring_interval", "recurring_rule_type")
    def _compute_recurrency_display(self):
        for task in self:
            display = False
            if task.is_recurring:
                display = "Every "
                # Avoid displaying "every 1 year"
                if task.recurring_interval and task.recurring_interval != 1:
                    display += f"{str(task.recurring_interval)} "
                if task.recurring_rule_type == "monthly":
                    display += "months"
                elif task.recurring_rule_type == "yearly":
                    display += "years"
            task.recurrency_display = display

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model
    def _name_search(self, name="", args=None, operator="ilike", limit=100):
        """Allows you to prioritize recurring tasks in the search"""
        if recurring_first := self._context.get("of_show_rec_icon_first"):
            task_ids = (
                list(super()._name_search(name, args + [["is_recurring", "=", recurring_first]], operator, limit)) or []
            )
            limit = limit - len(task_ids)
            if (
                task2_ids := list(
                    super()._name_search(
                        name,
                        [["is_recurring", "!=", recurring_first]],
                        operator,
                        limit,
                    )
                )
                or []
            ):
                task_ids.extend(task2_ids)
            return task_ids
        return super()._name_search(name, args, operator, limit)

    # --------------------------------------------------------------------------
    # Actions methods
    # --------------------------------------------------------------------------

    def action_button_view_of_service_request(self):
        self.ensure_one()
        action = self.env.ref("of_service.action_of_service_request").sudo().read()[0]
        action.update(
            {
                "domain": [("task_id", "in", self.ids)],
                "context": self._get_action_view_request_context(safe_eval(action["context"])),
            }
        )
        return self.mapped("request_ids")._get_service_request_action_views(action)

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _get_action_view_request_context(self, context=None):
        if context is None:
            context = {}
        context.update(
            {
                "default_partner_id": self.id,
                "default_address_id": self.id,
            }
        )
        return context
