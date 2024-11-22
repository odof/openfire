# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Customer orders",
        copy=False,
        domain="[('partner_id', '=', partner_id)]",
    )

    # Since `account.payment` is a delegated inheritance of `account.move`, we force the `ref` field to be stored
    # because we want `ref` to be in sync with the `move_id.ref` field when creating a payment from a sales order.
    # (see https://github.com/odoo/odoo/blob/16.0/addons/account/models/account_payment.py#L715)
    ref = fields.Char(related="move_id.ref", readonly=False, store=True)
