# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_default_deposit_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Default payment terms for deposit invoices",
        help="Set a default payment term for deposits invoices (e.g. 50% on order, 50% on delivery)."
        "This payment terms will replace that of the order when the deposit invoice is created.",
    )
