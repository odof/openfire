# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        move_comment_ids = self._propagate_comments_from_sale_order_to_invoice()
        values.update({"comment_template_ids": [Command.set(move_comment_ids)]})
        return values

    def _propagate_comments_from_sale_order_to_invoice(self):
        """Propagate comments from the sale order to the invoice based on the configuration.
        Returns a list of comment IDs to be set on the invoice.
        """
        propagate_comment_param = (
            self.env["ir.config_parameter"].sudo().get_param("of.sale.comment.template.propagate_comments")
        )
        if propagate_comment_param == "keep_comments":
            return self._keep_all_comments()
        if propagate_comment_param == "keep_top_comment":
            return self._keep_top_comments()
        return self._keep_bottom_comments() if propagate_comment_param == "keep_bottom_comment" else []

    def _keep_all_comments(self):
        """Return ids of comment templates to be set on the invoice.
        That could be the existing invoicing comment templates or the newly created ones.
        """
        return [
            self._update_invoicing_comment_template(order_comment_template).id
            for order_comment_template in self.comment_template_ids
        ]

    def _keep_top_comments(self):
        return self._get_comment_ids_based_on_position("before_lines")

    def _keep_bottom_comments(self):
        return self._get_comment_ids_based_on_position("after_lines")

    def _get_comment_ids_based_on_position(self, position):
        """Return ids of comment templates to be set on the invoice based on the given position.
        That could be the existing invoicing comment templates or the newly created ones.
        """
        return [
            self._update_invoicing_comment_template(order_comment_template).id
            for order_comment_template in self.comment_template_ids
            if order_comment_template.position == position
        ]

    def _update_invoicing_comment_template(self, order_comment_template):
        model_id = self.env["ir.model"].search([("model", "=", "account.move")])
        if model_id not in order_comment_template.model_ids:
            order_comment_template.model_ids = [Command.link(model_id.id)]
        return order_comment_template
