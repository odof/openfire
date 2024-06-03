# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_layout_category_active = fields.Boolean(string="Active Layout Category", default=True)
    of_show_products = fields.Boolean(string="Show Products", default=True)

    @api.onchange('of_show_products')
    def onchange_of_show_products(self):
        for line in self.order_line.filtered(lambda r: r.display_type != 'line_section'):
            line.of_show = self.of_show_products

    @api.onchange('of_layout_category_active')
    def onchange_of_layout_category_active(self):
        # Si jamais on cache les sections avancées, il faut toujours afficher les produits
        if not self.of_layout_category_active:
            self.of_show_products = True

    def get_sale_layout_summary_report(self):
        """
        Generate a summary report of the sale layout.

        This method calculates the lines to be included in the report, including totals and subtotals.
        It retrieves the highest-level sections and recursively collects the data for each section.
        It also calculates the totals for lines without sections.
        Finally, it calculates the total cost, total price, and total quantity for all lines.

        Returns:
            dict: A dictionary containing the summary report data, including sections and totals.

        """
        lines = []

        # Retrieve the highest-level sections
        sections = self.order_line.filtered(lambda r: r.display_type == 'line_section' and r.of_parent_node_id == 0)
        for section in sections:
            lines += self._sale_layout_recursive_data_section(section)

        summary = {'sections': lines}
        # Retrieve lines without sections
        lines_without_section = self.order_line.filtered(
            lambda r: r.display_type not in ['line_section', 'line_note'] and r.of_parent_node_id == 0
        )
        value = {
            'name': _("Without sections"),
            'cost': sum(lines_without_section.mapped('purchase_price')),
            'price': sum(lines_without_section.mapped('price_subtotal')),
            'qty': sum(lines_without_section.mapped('product_uom_qty')),
            'highlight': True,
        }
        summary['sections'].append(value)

        # Calculate the total
        total = {
            'name': _("Total"),
            'cost': 0,
            'price': 0,
            'qty': 0,
        }
        for line in self.order_line.filtered(lambda r: r.display_type not in ['line_section', 'line_note']):
            total['cost'] += line.purchase_price
            total['price'] += line.price_subtotal
            total['qty'] += line.product_uom_qty
        summary['total'] = total

        # Calculate the percentage of sales for each line of sections
        for line in summary['sections']:
            if total['price'] > 0:
                line['percent_price'] = round((line['price'] / total['price']) * 100, 2)
            else:
                line['percent_price'] = 0

        return summary

    def _sale_layout_recursive_data_section(self, section):
        child_lines = []
        # si on a des sous-sections, on va récupérer les données des sous-sections
        child_sections = self.order_line.filtered(
            lambda r: r.of_parent_node_id == section.of_node_id and r.display_type == 'line_section'
        )
        for child in child_sections:
            child_lines += self._sale_layout_recursive_data_section(child)

        # on fait la somme des lignes de cette section
        value_section = {
            'name': f"{section.of_section_name} - {section.name}",
            'cost': 0,
            'price': 0,
            'qty': 0,
            'highlight': section.of_parent_node_id == 0,
        }

        for line in self.order_line.filtered(
            lambda r: r.of_parent_node_id == section.of_node_id and r.display_type not in ['line_section', 'line_note']
        ):
            value_section['cost'] += line.purchase_price
            value_section['price'] += line.price_subtotal
            value_section['qty'] += line.product_uom_qty

        # on ajoute à cette section, la sommes des sous-sections
        for line in child_lines:
            value_section['cost'] += line['cost']
            value_section['price'] += line['price']
            value_section['qty'] += line['qty']

        return [value_section] + child_lines

    def action_button_show_summary(self):
        wz = self.env['of.sale.summary.wizard'].create({'sale_id': self.id})

        return {
            'name': _("Sale Summary"),
            'type': 'ir.actions.act_window',
            'res_model': 'of.sale.summary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wz.id,
        }
