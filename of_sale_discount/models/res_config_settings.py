# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_discount_on_invoice_line = fields.Boolean(
        string="(OF) Discount", implied_group='of_sale_discount.of_group_discount_on_invoice_line',
        group='account.group_account_invoice')
