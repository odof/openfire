# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPaymentMode(models.Model):
    _name = 'of.payment.mode'
    _description = "Payment Mode"
    _order = "journal_id asc"

    name = fields.Char(compute='_compute_name')
    shortname = fields.Char(related='payment_method_line_id.name', string="Short Name")
    journal_id = fields.Many2one(
        comodel_name='account.journal', string="Journal", required=True, ondelete='cascade', _order="id asc"
    )
    payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line', string="Payment Method Line", required=True, ondelete='cascade'
    )
    payment_type = fields.Selection(related='payment_method_line_id.payment_type')
    company_id = fields.Many2one(comodel_name='res.company', related='journal_id.company_id', string="Company")
    active = fields.Boolean()

    def _compute_name(self):
        for mode in self:
            mode.name = f"{mode.journal_id.name} - {mode.payment_method_line_id.name}"

    @api.model
    def action_update_mode_payment(self):
        """
        Update the payment modes based on the journals and payment method lines.

        This method searches for journals of type 'cash' or 'bank' and iterates over each journal.
        For each journal, it searches for payment method lines associated with that journal.
        If a payment mode does not already exist for the combination of journal and payment method line,
        a new payment mode is created.

        Returns:
            None
        """
        journal_ids = (
            self.env['account.journal'].with_context(active_test=False).search([('type', 'in', ['cash', 'bank'])])
        )
        for journal in journal_ids:
            for mode in self.env['account.payment.method.line'].search([('journal_id', '=', journal.id)]):
                if not self.env['of.payment.mode'].search(
                    [('journal_id', '=', journal.id), ('payment_method_line_id', '=', mode.id)]
                ):
                    self.env['of.payment.mode'].create(
                        {
                            'journal_id': journal.id,
                            'payment_method_line_id': mode.id,
                            'active': journal.active,
                        }
                    )
