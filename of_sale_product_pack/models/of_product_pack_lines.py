# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class OFProductPackLines(models.Model):
    _inherit = "of.product.pack.lines"

    pricelist_item_id = fields.Many2one(comodel_name="product.pricelist.item")
    parent_product_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Parent Product",
        ondelete="cascade",
        index=True,
        required=True,
    )

    _sql_constraints = [
        (
            "product_uniq",
            "unique(parent_product_id, product_id)",
            "Product must be only once on a pack !",
        ),
    ]

    def _prepare_procurement_values(self, group_id=False):
        """Copy of the original method in sale.order.line to manage pack lines as well"""
        parent_line_procurement_values = self.parent_product_id._prepare_procurement_values(group_id)
        parent_line_procurement_values.update(
            {
                "sale_line_id": self.parent_product_id.id,
            }
        )
        return parent_line_procurement_values

    def get_sale_order_line_vals(self, line, order):
        """
        Récupération de la fonction get_sale_order_line_vals de product.pack.line mais pour of.product.pack.lines

        Args:
            line (sale.order.line): La ligne de commande pour laquelle on souhaite récupérer les valeurs
            order (sale.order): La commande de la ligne de commande

        Returns:
            dict: Le dictionnaire de valeurs à passer au write de sale.order.line
        """
        self.ensure_one()
        quantity = self.quantity * line.product_uom_qty
        line_vals = {
            "order_id": order.id,
            "sequence": line.sequence,
            "product_id": self.product_id.id or False,
            "pack_parent_line_id": line.id,
            "pack_depth": line.pack_depth + 1,
            "company_id": order.company_id.id,
            "pack_modifiable": line.product_id.pack_modifiable,
            "product_uom_qty": quantity,
        }
        sol = line.new(line_vals)
        sol._onchange_product_id_warning()
        vals = sol._convert_to_write(sol._cache)
        pack_price_types = {"totalized", "ignored"}
        sale_discount = 0.0
        if line.product_id.pack_component_price == "detailed":
            sale_discount = 100.0 - ((100.0 - sol.discount) * (100.0 - self.sale_discount) / 100.0)
        elif line.product_id.pack_type == "detailed" and line.product_id.pack_component_price in pack_price_types:
            vals["price_unit"] = 0.0
        vals.update(
            {
                "discount": sale_discount,
                "name": "{}{}".format("> " * (line.pack_depth + 1), sol.name),
            }
        )
        return vals
