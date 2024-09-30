# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    request_address_ids = fields.One2many(
        comodel_name="of.service.request",
        inverse_name="address_id",
        string="Service Request",
        context={"active_test": False},
    )
    request_partner_ids = fields.One2many(
        comodel_name="of.service.request",
        inverse_name="partner_id",
        string="Partner Service Request",
        context={"active_test": False},
        help="Service requests linked to the partner, including requests from associated contacts",
    )
    request_to_schedule_ids = fields.Many2many(
        comodel_name="of.service.request", string="SR to schedule", compute="_compute_requests"
    )
    request_to_schedule_count = fields.Integer(string="SR to schedule count", compute="_compute_requests")
    recurring_request_ids = fields.Many2many(
        comodel_name="of.service.request", string="Recurring SR", compute="_compute_requests"
    )
    recurring_request_count = fields.Integer(string="Number of recurring SR", compute="_compute_requests")

    def _compute_requests(self):
        request_obj = self.env["of.service.request"]
        for partner in self:
            request_ids = request_obj.search(
                [
                    "|",
                    ("partner_id", "child_of", partner.id),
                    ("address_id", "child_of", partner.id),
                ]
            )
            partner.request_to_schedule_ids = request_ids.filtered(
                lambda s: s.state in ["draft", "to_plan", "to_plan_quickly", "part_planned", "late"]
            )
            partner.request_to_schedule_count = len(partner.request_to_schedule_ids)
            partner.recurring_request_ids = request_ids.filtered(
                lambda s: s.recurrency and s.state not in ["draft", "done", "cancel"]
            )
            partner.recurring_request_count = len(partner.recurring_request_ids)

    def action_button_schedule_intervention(self):
        self.ensure_one()
        action = self.env.ref("of_service.action_of_service_request").read()[0]
        action.update(
            {
                "name": _("Schedule an intervention"),
                "view_mode": "form",
                "view_ids": False,
                "view_id": self.env.ref("of_service.of_service_request_view_form").id,
                "views": False,
                "target": "new",
                "context": {
                    "default_partner_id": self.id,
                    "default_address_id": self.address_get(adr_pref=["delivery"]).get("delivery") or self.id,
                    "default_recurrency": False,
                    "default_next_date": fields.Date.today(),
                    "default_origin": _("[Partner] %s") % self.name,
                    "hide_schedule_button": True,
                    "default_type_id": self.env.ref("of_service.of_service_request_type_maintenance").id,
                },
            }
        )
        return action

    def action_button_view_service_request(self):
        self.ensure_one()
        return self._get_action_view_service_request()

    def action_button_view_recurring_service_request(self):
        self.ensure_one()
        return self._get_action_view_service_request(recurrency=True)

    def _get_action_view_service_request(self, recurrency=False):
        """
        Get the action view for the service request.

        :param requests: the service requests to display
        :param recurrency: whether to display the recurring service requests
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("of_service.action_of_service_request")
        action.update(
            {
                "domain": [
                    "|",
                    ("partner_id", "child_of", self.ids),
                    ("address_id", "child_of", self.ids),
                ],
                "res_id": self.id,
                # Override the context to get rid of the default filtering on operation type
                "context": self._get_action_view_service_request_context(recurrency=recurrency),
            }
        )
        return action

    def _get_action_view_service_request_context(self, recurrency=False, context=None):
        if context is None:
            context = {}
        context.update(
            {
                "default_partner_id": self.id,
                "default_address_id": self.address_get(adr_pref=["delivery"]).get("delivery") or self.id,
                "default_recurrency": recurrency,
                "default_next_date": fields.Date.today(),
                "default_origin": _("[Partner] %s") % self.name,
                "search_default_filter_draft": True,
                "search_default_filter_to_plan": True,
                "search_default_filter_part_planned": True,
                "search_default_filter_late": True,
                "hide_schedule_button": True,
            }
        )
        return context
