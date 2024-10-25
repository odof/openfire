# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, _, api, fields, models

from .tools import _get_list_from_parameter


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    of_is_poujoulat_partner = fields.Boolean(string="Poujoulat partner", compute="_compute_of_is_poujoulat_partner")
    of_poujoulat_sent = fields.Boolean(string="Sent to CatEstimate")
    of_poujoulat_error = fields.Text(string="Sending error Poujoulat")

    @api.depends("partner_id")
    def _compute_of_is_poujoulat_partner(self):
        """
        Sets 'of_is_poujoulat_partner' to True if the purchase order's partner is in the
        list of configured Poujoulat partners.
        """
        partner_ids = _get_list_from_parameter(self, "of.connector.poujoulat.partner_ids")
        for order in self:
            order.of_is_poujoulat_partner = order.partner_id.id in partner_ids

    def action_button_send_poujoulat_cart(self):
        """Prepares and opens a wizard to send Poujoulat products in the purchase order.

        Returns:
            dict: An action to open the wizard window with prefilled product lines.
        """
        self.ensure_one()

        brand_ids = _get_list_from_parameter(self, "of.connector.poujoulat.brand_ids")
        line_values = [
            Command.create(
                {
                    "product_id": line.product_id.id,
                    "quantity": line.product_qty,
                }
            )
            for line in self.mapped("order_line").filtered(lambda li: li.product_id.brand_id.id in brand_ids)
        ]
        values = {"purchase_id": self.id, "sent": self.of_poujoulat_sent}
        if line_values:
            values["line_ids"] = line_values
        wizard = self.env["of.poujoulat.cart.wizard"].create(values)

        return {
            "name": _("Ordering Poujoulat products"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "of.poujoulat.cart.wizard",
            "res_id": wizard.id,
            "target": "new",
            "context": self.env.context.copy(),
        }
