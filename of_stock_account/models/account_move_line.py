# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import api, fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    of_product_brand_id = fields.Many2one(
        comodel_name="of.product.brand",
        related="product_id.brand_id",
        string="Brand",
        store=True,
        index=True,
        readonly=True,
    )

    @api.depends("product_id", "journal_id")
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            line.name = self._recompute_line_name(line)

    def _write(self, vals):
        for field in vals:
            if field != "of_product_brand_id":
                break
        else:  # No other field than of_product_brand_id
            self = self.sudo()
        return super(AccountInvoiceLine, self)._write(vals)

    def _recompute_line_name(self, line):
        """Recompute the name of the invoice line based on the product's name and the brand's description_sale."""
        line_name = line.name
        if line.product_id.brand_id.use_brand_description_sale:
            # Recalcul du libelllé de la ligne
            line_name = line.product_id.name_get()[0][1]
            # Only inline templates are supported here.
            # ie: {{ description_sale and '\n' + description_sale or '' }}
            brand_desc = self.env["mail.template"]._render_template(
                line.product_id.brand_id.description_sale,
                "product.product",
                [line.product_id.id],
                post_process=False,
            )[line.product_id.id]
            line_name += "\n%s" % brand_desc
        if line.product_id.brand_id.show_in_sales:
            # Ajout de la marque dans le descriptif de l'article
            brand_code = f"{line.product_id.brand_id.name} - "
            # This regex will match the first occurrence of "[XXXX]" in the product's name as the default code
            # and will capture the rest of the string.
            # So if the product's name is "[XXXX] This is the product's [YYYY] name" it will capture groups
            # as : "[XXXX] " and "This is the product's [YYYY] name"
            regex = r"(^\[\S+\] )(.*)"
            if re.search(regex, line_name) is not None:
                # product's name is required so we should always have 2 groups here
                subst = f"\\g<1>{brand_code}\\g<2>"
                line_name = re.sub(regex, subst, line_name, 0, re.MULTILINE)
            else:
                line_name = brand_code + line_name
        return line_name
