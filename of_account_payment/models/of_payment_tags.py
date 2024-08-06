# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPaymentTags(models.Model):
    """Tags of payment"""

    _name = "of.payment.tags"
    _description = "Payment Category"

    name = fields.Char(string="Category name", help="Category name")
    color = fields.Integer(string="Color")
    description = fields.Text(string="Category description", help="Payment category description")

    _sql_constraints = [('name_uniq', 'unique (name)', "The category name already exists!")]
