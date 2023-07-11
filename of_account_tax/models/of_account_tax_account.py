# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OfAccountTaxAccount(models.Model):
    """Tax Accounts : copied from class account.fiscal.position.account"""

    _name = 'of.account.tax.account'
    _description = __doc__
    _rec_name = 'tax_id'

    tax_id = fields.Many2one(comodel_name='account.tax', string="Tax", required=True, ondelete='cascade')
    account_src_id = fields.Many2one(
        comodel_name='account.account', string="Item account", domain=[('deprecated', '=', False)], required=True
    )
    account_dest_id = fields.Many2one(
        comodel_name='account.account',
        string="Account to be used instead",
        domain=[('deprecated', '=', False)],
        required=True,
    )

    _sql_constraints = [
        (
            'of_account_src_dest_uniq',
            'unique (tax_id,account_src_id,account_dest_id)',
            "You cannot create two identical account correspondences on the same tax.",
        )
    ]
