# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_sale_type_id = fields.Many2one(comodel_name='of.sale.type', string="Sale order type")

    class AccountInvoiceLine(models.Model):
        _inherit = 'account.invoice.line'

        of_sale_type_id = fields.Many2one(related='invoice_id.of_sale_type_id', string="Sale order type", readonly=True,
                                          store=True)

    def _get_refund_common_fields(self):
        common_fields = ['of_sale_type_id']
        return (super(AccountInvoice, self)._get_refund_common_fields() or []) + common_fields
