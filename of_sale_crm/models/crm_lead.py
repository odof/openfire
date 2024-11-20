# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    of_customer_state = fields.Selection(related="partner_id.of_customer_state", required=False)

    # -------------------------------------------------------------------------
    # Onchange methods
    # -------------------------------------------------------------------------

    @api.onchange("partner_id")
    def _onchange_partner_id_warning(self):
        if not (partner := self.partner_id):
            return
        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_lead_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_lead_warn and partner.invoice_warn != "no-message":
            if partner.invoice_warn != "block" and partner.parent_id and partner.parent_id.invoice_warn == "block":
                partner = partner.parent_id
            warning = {"title": _("Warning for %s") % partner.name, "message": partner.invoice_warn_msg}
            if partner.invoice_warn == "block":
                self.partner_id = False
            return {"warning": warning}

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def write(self, vals):
        saved_values = {
            opportunity: {
                "probability": opportunity.probability,
                "stage_id": opportunity.stage_id,
                "active": opportunity.active,
            }
            for opportunity in self
        }
        res = super().write(vals)
        if not self.env.context.get("of_avoid_customer_state_compute"):
            self._handle_of_customer_state_update(vals, saved_values)
        return res

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_set_lost(self, **additional_values):
        res = super().action_set_lost(**additional_values)
        orders = self.mapped("order_ids").filtered(lambda order: order.state in ["draft", "sent"])
        orders and orders._action_cancel()
        return res

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _prepare_opportunity_quotation_context(self):
        quotation_context = super()._prepare_opportunity_quotation_context()
        quotation_context["default_of_referred_id"] = self.of_referred_id.id
        quotation_context["default_of_canvasser_id"] = self.of_canvasser_id.id
        return quotation_context

    def _handle_of_customer_state_update(self, vals, saved_values):
        if (
            "probability" not in vals
            and "stage_id" not in vals
            and "active" not in vals
            and "lost_reason_id" not in vals
        ):
            return

        def _get_all_parent_partners(partners):
            all_partners = partners
            for partner in partners:
                current = partner.parent_id
                while current:
                    if current not in partners:
                        all_partners |= current
                    current = current.parent_id
            return all_partners

        to_process = self.filtered(
            lambda o: (
                ((o.probability == 100) != (saved_values[o]["probability"] == 100))
                or (o.stage_id.is_won != saved_values[o]["stage_id"].is_won)
                or ("lost_reason_id" in vals and o.active != saved_values[o]["active"])
            )
        )

        if to_process:
            partners = to_process.mapped("partner_id")
            all_partners = _get_all_parent_partners(partners)
            all_partners and all_partners._compute_of_customer_state()
