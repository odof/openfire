# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

from .utils import compute_discount


class OfImportProductConfigTemplate(models.AbstractModel):
    _name = 'of.import.product.config.template'
    _description = "Class for customizable parameters in tariff import configuration"

    of_import_sale_price = fields.Char(
        string="Sale price untaxed",
        help="""Change to apply on untaxed public price to compute sale price.

Examples :
    - ppht : Keep public price untaxed
    - ppht * 1.05 + 10 : Increases the selling price by 5%, plus 10€
    - pa * 100 / 60 : Sells the item to achieve a margin of 40% on the purchase price (not on the cost price!).""",
    )
    of_import_discount = fields.Char(
        string="Discount",
        help="""Discount to be applied to items from this supplier.
        The discount is applied to the list price to calculate the purchase price.

Examples :
    - 40.5 : Force a discount of 40.5% (Attention, use a period and not a comma!)
    - cumul(10,5) : Apply the recommended discount, then a discount of 10%, then a discount of 5%
    - cumul(14.5) : Equivalent to the previous line, a discount of 10% then 5% totals 14.5% in total.""",
    )
    of_import_cost_price = fields.Char(
        string="Cost Price",
        help="""Allows the calculation of the cost price based on the purchase price.

Examples :
    - pa : Retains the purchase price calculated from the formulas of the selling price and the discount.
    - pa * 1.05 + 20 : Purchase price increased by 5%, then increased by 20€.
""",
    )
    of_import_categ_id = fields.Many2one(comodel_name='product.category', string="Category")

    @api.constrains('of_import_sale_price', 'of_import_discount', 'of_import_cost_price')
    def _check_description(self):
        """
        Function to check the validity of formulas entered.
        A formula, if entered, cannot consist solely of blank spaces.
        A formula must be evaluable without error, using the variables provided in eval_dict.
        A formula, if entered, must return a numeric value (integer or float).
        """
        # Set of values to test the validity of formulas entered
        eval_dict = self._get_eval_dict_check()

        for record in self:
            for field in (
                'of_import_sale_price',
                'of_import_discount',
                'of_import_cost_price',
            ):
                code = record[field]
                if not code:
                    continue
                if not code.strip():
                    raise ValidationError(
                        "A formula must not consist solely of spaces.\n"
                        "You must clear the field or provide it with a correct formula if it is required."
                        " (field : %(field)s, formula: %(code)s"
                    ) % {'field': self._fields[field].string, 'code': code}
                if field == 'of_import_sale_price' and code.strip() == 'pv':
                    continue
                if field == 'of_import_cost_price' and code.strip() == 'pr':
                    continue
                try:
                    value = safe_eval(code, eval_dict)
                except Exception as e:
                    raise ValidationError(
                        "An error occurred while validating the formula.\n"
                        "(field : %(field)s, formula : %(code)s, error : %(e)s)"
                    ) % {
                        'field': self._fields[field].string,
                        'code': code,
                        'e': e,
                    } from e

                if value and not isinstance(value, (int, float)):
                    raise ValidationError(
                        "The return format of the function is not as expected."
                        " (field : %(field)s, formula : %(code)s)\n"
                        "This error may occur if you have used a comma instead of a period as the decimal separator."
                    ) % {'field': self._fields[field].string, 'code': code}

    def _get_eval_dict_check(self):
        """
        Function to return the set of values to test the validity of formulas entered.
        Watch out if you change keys, you must also change the keys in the help of the fields.
        They are used to explain the user what he can use in the formulas.
        """
        return {
            'ppht': 100,
            'cumul': compute_discount,
            'pa': 50,
            # Pricing structure
            'tr_a': 10,
            'tr_v': 10,
            'coef': 10,
            'fr_l': 10,
            'taxe': 10,
            'fr_d': 10,
        }

    @api.model
    def _get_config_field_list(self):
        return [
            'of_import_sale_price',
            'of_import_discount',
            'of_import_cost_price',
            'of_import_categ_id',
        ]
