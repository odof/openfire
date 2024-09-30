# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _order = "order_id, sequence, of_position_node, id"

    of_section_name = fields.Char(string="Section name")
    of_node_id = fields.Integer(string="Node ID")
    of_parent_node_id = fields.Integer(string="Parent Node ID")
    of_position_node = fields.Integer(string="Node's Position")
    of_level = fields.Integer(string="Level")
    of_show = fields.Boolean(string="Show line", default=True)

    def _get_product_section(self):
        self.ensure_one()
        # La section est forcément la ligne où le of_node_id = of_parent_node_id de l'article
        return self.env["sale.order.line"].search(
            [
                ("order_id", "=", self.order_id.id),
                ("of_node_id", "=", self.of_parent_node_id),
            ],
            limit=1,
        )

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id)

        # Les données ici sont nécessaires pour calculer le champs of_section sur le stock picking.
        # Dans le stock picking on ne récupère que les lignes qui ont des articles.
        # On doit donc, pour chaque ligne d'article, ramener la section dans laquelle est cet article
        # et retourner la numérotation de la section et son nom.
        if self.display_type not in ["line_section", "line_note"]:
            section = self._get_product_section()
            values.update({"of_section": f"{section.of_section_name} - {section.name}"})
        else:
            values.update({"of_section": f"{self.of_section_name} - {self.name}"})
        return values

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        values.update(
            {
                "of_section_name": self.of_section_name,
                "of_node_id": self.of_node_id,
                "of_parent_node_id": self.of_parent_node_id,
                "of_position_node": self.of_position_node,
                "of_level": self.of_level,
            }
        )

        return values
