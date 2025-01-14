# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    of_layout_category_active = fields.Boolean(string="Active Layout Category", default=True)
