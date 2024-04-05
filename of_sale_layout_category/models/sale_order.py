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

    def show_summary(self):
        wz = self.env['of.sale.summary.wizard'].create({'sale_id': self.id})

        return {
            'name': _("Sale Summary"),
            'type': 'ir.actions.act_window',
            'res_model': 'of.sale.summary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wz.id,
        }
