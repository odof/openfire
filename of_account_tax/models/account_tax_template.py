# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    of_account_ids = fields.One2many(
        comodel_name="of.account.tax.account.template", inverse_name="template_tax_id", string="Account matching"
    )
