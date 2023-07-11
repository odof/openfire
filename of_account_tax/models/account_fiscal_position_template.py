# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    of_default_tax_ids = fields.Many2many(
        comodel_name='account.tax.template',
        relation='account_fiscal_position_template_account_tax_template_rel',
        column1='account_fiscal_position_template_id',
        column2='account_tax_template_id',
        string="Default taxes",
    )
