# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # Uniformisation de la méthode de coût sur les sociétés (effectif si of_base_multicompany est installé)
    property_cost_method = fields.Selection(of_unify_companies=True)
    of_stock_update_standard_price = fields.Boolean(
        string="Update the cost of items following stock movements", default=True
    )
    of_import_update_standard_price = fields.Boolean(string="Update the cost of items following imports")
    of_sale_cost = fields.Selection(
        selection=[('theoretical', "Theoretical cost"), ('standard', "Standard cost")],
        string="Cost to sales",
        help="The chosen cost will be included in sales orders and invoices.",
        required=True,
        default='theoretical',
    )

    def copy_data(self, default=None):
        new_defaults = {
            'property_account_creditor_price_difference_categ': self.property_account_creditor_price_difference_categ,
            'property_account_income_categ_id': self.property_account_income_categ_id,
            'property_account_expense_categ_id': self.property_account_expense_categ_id,
            'property_stock_account_input_categ_id': self.property_stock_account_input_categ_id,
            'property_stock_account_output_categ_id': self.property_stock_account_output_categ_id,
            'property_stock_valuation_account_id': self.property_stock_valuation_account_id,
            'property_stock_journal': self.property_stock_journal,
        }
        default = dict(new_defaults, **(default or {}))
        return super().copy_data(default)

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == 'of_unify_companies' or super()._valid_field_parameter(field, name)
