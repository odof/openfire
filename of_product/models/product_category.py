# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    route_ids = fields.Many2many(
        comodel_name='stock.route', relation='stock_location_route_categ', column1='categ_id',
        column2='route_id', string="Routes", domain=[('product_categ_selectable', '=', True)], copy=True)
    of_layout_id = fields.Many2one(comodel_name='sale.layout_category', string="Layout")
    # Uniformisation de la méthode de coût sur les sociétés (effectif si of_base_multicompany est installé)
    property_cost_method = fields.Selection(of_unify_companies=True)
    of_stock_update_standard_price = fields.Boolean(
        string="Update the cost of items following stock movements", default=True)
    of_import_update_standard_price = fields.Boolean(string="Update the cost of items following imports")
    of_sale_cost = fields.Selection(
        selection=[('theoretical', "Theoretical cost"), ('standard', "Standard cost")], string="Cost to sales",
        help="The chosen cost will be included in sales orders and invoices.", required=True,
        default='theoretical')

    def copy_data(self, default=None):
        new_defaults = {
            'name': _("%s (copy)") % (self.name),
            'property_account_creditor_price_difference_categ': self.property_account_creditor_price_difference_categ,
            'property_account_income_categ_id': self.property_account_income_categ_id,
            'property_account_expense_categ_id': self.property_account_expense_categ_id,
            'property_stock_account_input_categ_id': self.property_stock_account_input_categ_id,
            'property_stock_account_output_categ_id': self.property_stock_account_output_categ_id,
            'property_stock_valuation_account_id': self.property_stock_valuation_account_id,
            'property_stock_journal': self.property_stock_journal,
        }
        default = dict(new_defaults, **(default or {}))
        return super(ProductCategory, self).copy_data(default)
