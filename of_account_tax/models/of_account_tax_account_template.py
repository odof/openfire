# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OfAccountTaxAccountTemplate(models.Model):
    """Tax accounts template"""

    _name = 'of.account.tax.account.template'
    _description = __doc__
    _rec_name = 'template_tax_id'

    template_tax_id = fields.Many2one(
        comodel_name='account.tax.template', string="Tax template", required=True, ondelete='cascade'
    )
    account_src_id = fields.Many2one(
        comodel_name='account.account.template',
        string="Item account",
        domain=[('deprecated', '=', False)],
        required=True,
    )
    account_dest_id = fields.Many2one(
        comodel_name='account.account.template',
        string="Account to be used instead",
        domain=[('deprecated', '=', False)],
        required=True,
    )

    _sql_constraints = [
        (
            'of_account_src_dest_uniq',
            'unique (template_tax_id, account_src_id, account_dest_id)',
            "You cannot create two identical account correspondences on the same tax.",
        )
    ]
