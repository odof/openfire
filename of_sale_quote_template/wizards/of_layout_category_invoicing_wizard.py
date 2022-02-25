# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFLayoutCategoryInvoicingWizard(models.TransientModel):
    _name = 'of.layout.category.invoicing.wizard'
    _description = u"Wizard de facturation par sections"

    order_id = fields.Many2one(comodel_name='sale.order', string=u'Commande', required=True)
    layout_category_ids = fields.Many2many(
        comodel_name='of.sale.order.layout.category',
        relation='of_layout_category_invoicing_layout_category_rel', string=u'Lignes de section', required=True)

    def action_done(self):
        invoice_vals = self.order_id._prepare_invoice()
        invoice = self.env['account.invoice'].create(invoice_vals)

        for line in self.layout_category_ids.mapped('order_line_without_child_ids')\
                .filtered(lambda l: l.invoice_status == 'to invoice'):
            line.invoice_line_create(invoice.id, line.product_uom_qty)

        invoice.compute_taxes()
        invoice.message_post_with_view(
            'mail.message_origin_link', values={'self': invoice, 'origin': self.order_id},
            subtype_id=self.env.ref('mail.mt_note').id)

        order_line = self.order_id.order_line._compute_invoice_status()
        if order_line:
            order_line._compute_invoice_status()

        return {
            'name': u"Création de la facture",
            'view_id': self.env.ref('account.invoice_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'res_id': invoice.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
