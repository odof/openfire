# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_canvasser_id = fields.Many2one(
        comodel_name='res.users',
        string="Prospecteur",
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user,
    )

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        self.update_of_customer_state()
        return res

    @api.multi
    def update_of_customer_state(self):
        partners = self.env['res.partner']
        for invoice in self:
            if (
                invoice.partner_id.of_customer_state == 'lead'
                and invoice.partner_id not in partners
                and invoice.partner_id.customer
            ):
                partners += invoice.partner_id
        partners and partners.write({'of_customer_state': 'customer'})
