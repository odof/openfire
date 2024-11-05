# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if not line.product_id.of_industry_id or not line.product_id.of_industry_id.show_in_sales:
                continue

            if industry_content_list := line._get_industry_content_list():
                line.name = line.name + "\n\n" + "\n".join(industry_content_list)

    def _get_industry_content_list(self):
        """
        Generate a list of industry content lines for the sale order line.
        Industry content is fetched from the product's industry and is processed to remove empty lines.
        That content is a template string that can be rendered with the product's data. (e.g. {{ product.name }}))

        Returns:
            list: A list of strings representing the processed industry content lines.
        """
        self.ensure_one()

        # On génère le contenu
        industry_content = self.env["mail.render.mixin"]._render_template(
            self.product_id.of_industry_id._get_content(),
            self.product_id._name,
            self.product_id.ids,
        )[self.product_id.id]

        # Si des informations sont manquantes, on retire les lignes vides \n
        # Mais on se laisse la possibilité de laisser des lignes vides avec \r
        industry_content_list = [line for line in industry_content.split("\n") if line == "\r" or line.strip()]

        # Si deux sauts de ligne \r se suivent on en garde que un
        industry_content_list = [
            industry_content_list[i]
            for i in range(len(industry_content_list))
            if (i == 0) or industry_content_list[i] != "\r" or industry_content_list[i] != industry_content_list[i - 1]
        ]
        return industry_content_list
