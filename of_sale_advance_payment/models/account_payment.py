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
