# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_customer_state = fields.Selection(
        selection=[("lead", "Prospect"), ("customer", "Signed customer"), ("other", "Other")],
        string="Customer State",
        compute="_compute_of_customer_state",
        default="lead",
        store=True,
        readonly=False,
        help="This field is only useful for customer partners."
        "A customer is considered a prospect as long as he/she has neither confirmed an order nor validated "
        "an invoice. This field is updated automatically on order confirmation and invoice validation.",
    )
    of_is_lead_warn = fields.Boolean(string="Leads warning")

    def _add_missing_default_values(self, values):
        if not values.get("of_customer_state", False):
            values["of_customer_state"] = "lead"
        return super()._add_missing_default_values(values)

    @api.depends("customer_rank", "supplier_rank", "parent_id.customer_rank", "parent_id.supplier_rank")
    def _compute_of_customer_state(self):
        """
        A partner is considered a signed customer if its `customer_rank` is > 0 or if it has an opportunity won,
        other if its `supplier_rank` > 0 and prospect otherwise.
        """
        lead_obj = self.env["crm.lead"]
        for partner in self:
            customer_state = "lead"
            leads = lead_obj.search([("partner_id", "=", partner.id)])
            if (
                partner.customer_rank
                or (partner.parent_id and partner.parent_id.customer_rank)
                or any(lead.probability == 100 for lead in leads)
            ):
                customer_state = "customer"
            elif partner.supplier_rank:
                customer_state = "other"
            partner.of_customer_state = customer_state

    @api.depends("of_is_lead_warn")
    def _compute_of_is_warn(self):
        has_warn = self.filtered("of_is_lead_warn")
        for partner in has_warn:
            partner.of_is_warn = True
        partners_left = self - has_warn
        super(ResPartner, partners_left)._compute_of_is_warn()
