# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models


class OFSaleOrderAddQuoteWizard(models.TransientModel):
    """Wizard to add a quote to a sales order"""

    _name = 'of.sale.order.add.quote.wizard'
    _description = __doc__

    order_id = fields.Many2one(comodel_name='sale.order', string="Sales order to update")
    quote_id = fields.Many2one(comodel_name='sale.order', string="Quote to add")
    addable_quote_ids = fields.Many2many(
        comodel_name='sale.order', compute='_compute_addable_quote_ids', string="Addable quotes"
    )

    @api.depends('order_id')
    def _compute_addable_quote_ids(self):
        for rec in self:
            addable_quote = self.env['sale.order'].search(
                [
                    ('partner_invoice_id', '=', rec.order_id.partner_invoice_id.id),
                    ('partner_shipping_id', '=', rec.order_id.partner_shipping_id.id),
                    ('company_id', '=', rec.order_id.company_id.id),
                    ('state', 'in', ['draft', 'sent']),
                ]
            )
            if rec.order_id:
                rec.addable_quote_ids = [Command.set(addable_quote.ids)] if addable_quote else False
            else:
                rec.addable_quote_ids = False

    def action_button_add_quote(self):
        """Copy lines of the selected quote to add them in the source order and cancel the added quote"""
        self.ensure_one()
        for line in self.quote_id.order_line:
            new_name = line.name + "\n\n" + _("Line added from the complementary quote %s") % self.quote_id.name
            line.copy(
                {
                    'order_id': self.order_id.id,
                    'name': new_name,
                }
            )

        return self.quote_id.action_cancel()
