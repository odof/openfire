# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        values = super()._prepare_invoice()

        # Récupérer la configuration pour la propagation des commentaires
        propagate_comment_param = (
            self.env["ir.config_parameter"].sudo().get_param("of.sale.comment.template.propagate_comments")
        )
        if propagate_comment_param == "keep_top_comment":
            # Mettre à jour les valeurs de commentaires
            values.update(
                {
                    "of_top_comment": self.of_top_comment,
                }
            )

        if propagate_comment_param == "keep_bottom_comment":
            values.update(
                {
                    "of_bottom_comment": self.of_bottom_comment,
                }
            )
        if propagate_comment_param == "keep_comments":
            values.update(
                {
                    "of_top_comment": self.of_top_comment,
                    "of_bottom_comment": self.of_bottom_comment,
                }
            )

        return values
