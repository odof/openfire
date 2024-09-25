# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, api, fields, models


class AccountVoucherWizard(models.TransientModel):
    _inherit = 'account.voucher.wizard'

    of_payment_mode_id = fields.Many2one(
        comodel_name='of.payment.mode',
        string="Payment Mode",
        domain="[('payment_type', '=', payment_type)]",
    )
    of_payment_ref = fields.Char(size=64, string="Payment reference")
    of_tag_ids = fields.Many2many(comodel_name='of.payment.tags', string="Payment tags")
    partner_bank_id = fields.Many2one(
        comodel_name='res.partner.bank', string="Recipient Bank", related='journal_id.bank_account_id'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        sale_ids = self.env.context.get("active_ids", [])
        if not sale_ids:
            return res
        sale_id = fields.first(sale_ids)
        sale = self.env['sale.order'].browse(sale_id)
        if 'amount_total' in fields_list:
            res.update(
                {
                    'payment_ref': sale.name,
                }
            )

        return res

    @api.onchange('of_payment_mode_id')
    def _onchange_of_payment_mode_id(self):
        if self.of_payment_mode_id:
            self.journal_id = self.of_payment_mode_id.journal_id
        else:
            self.journal_id = False

    def _prepare_payment_vals(self, sale):
        res = super()._prepare_payment_vals(sale)
        res.update(
            {
                'of_payment_mode_id': self.of_payment_mode_id.id,
                'of_tag_ids': [Command.set(self.of_tag_ids.ids)],
                'payment_reference': self.of_payment_ref,
            }
        )
        return res
