# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    of_default_deposit_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Default payment terms for deposit invoices",
        related="company_id.of_default_deposit_payment_term_id",
        readonly=False,
    )
