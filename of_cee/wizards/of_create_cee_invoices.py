# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class OFCreateCEEInvoices(models.TransientModel):
    _name = 'of.create.cee.invoices'

    @api.model
    def default_get(self, fields):
        result = super(OFCreateCEEInvoices, self).default_get(fields)
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_ids'):
            orders = self.env['sale.order'].browse(self._context.get('active_ids'))
            cee_product_categ_id = self.env['ir.values'].get_default('sale.config.settings', 'of_cee_product_categ_id')

            not_validated_orders = orders.filtered(lambda o: o.state != 'sale')
            orders -= not_validated_orders

            no_cee_product_orders = orders.filtered(
                lambda o: not o.order_line.filtered(
                    lambda l: l.product_id.categ_id.id == cee_product_categ_id and l.product_uom_qty))
            orders -= no_cee_product_orders

            already_invoiced_orders = orders.filtered(
                lambda o: o.order_line.filtered(
                    lambda l: l.product_id.categ_id.id == cee_product_categ_id and
                    l.invoice_lines.filtered(lambda inv_line: inv_line.invoice_id.of_is_cee)))
            orders -= already_invoiced_orders

            info_txt = u"Commande(s) sélectionnée(s) : %s\n" % \
                       (len(orders) + len(not_validated_orders) + len(no_cee_product_orders)
                        + len(already_invoiced_orders))
            info_txt += u"Commande(s) avec article CEE facturable : %s\n" % len(orders)
            info_txt += u"Commande(s) sans article CEE facturable : %s\n" % \
                        (len(not_validated_orders) + len(no_cee_product_orders) + len(already_invoiced_orders))

            if orders:
                result['ok'] = True
                result['order_ids'] = [(6, 0, [orders.ids])]

            if not_validated_orders or no_cee_product_orders or already_invoiced_orders:
                result['error'] = True
                info_txt += u"\nDétail des commandes sans article CEE facturable :"
                if not_validated_orders:
                    info_txt += u"\n- Commande(s) non validée(s) :\n"
                    info_txt += u"\n".join(
                        ['    - %s' % name for name in not_validated_orders.mapped('name')])
                if no_cee_product_orders:
                    info_txt += u"\n- Commande(s) sans article CEE :\n"
                    info_txt += u"\n".join(
                        ['    - %s' % name for name in no_cee_product_orders.mapped('name')])
                if already_invoiced_orders:
                    info_txt += u"\n- Commande(s) avec article CEE déjà facturé :\n"
                    info_txt += u"\n".join(
                        ['    - %s' % name for name in already_invoiced_orders.mapped('name')])
            result['info_txt'] = info_txt
        return result

    order_ids = fields.Many2many(comodel_name='sale.order', string=u"Factures à relancer")
    ok = fields.Boolean()
    error = fields.Boolean()
    info_txt = fields.Text()

    @api.multi
    def create_cee_invoices(self):
        cee_product_categ_id = self.env['ir.values'].get_default('sale.config.settings', 'of_cee_product_categ_id')
        invoices = {}
        references = {}
        invoices_origin = {}
        invoices_name = {}
        for order in self.order_ids:
            cee_lines = order.order_line.filtered(
                lambda l: l.product_id.categ_id.id == cee_product_categ_id and l.product_uom_qty and
                not l.invoice_lines.filtered(lambda inv_line: inv_line.invoice_id.of_is_cee))
            for cee_line in cee_lines:
                if cee_line.product_id.seller_ids:
                    partner = cee_line.product_id.seller_ids[0].name
                    group_key = (partner.id, order.company_id.id)

                    # Create invoice
                    if group_key not in invoices:
                        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
                        if not journal_id:
                            raise UserError(u"Veuillez définir un journal de vente pour cette entreprise.")
                        invoice_vals = {
                            'name': order.client_order_ref or '',
                            'origin': order.name,
                            'type': 'out_invoice',
                            'account_id': partner.property_account_receivable_id.id,
                            'partner_id': partner.id,
                            'partner_shipping_id': partner.id,
                            'journal_id': journal_id,
                            'currency_id': order.pricelist_id.currency_id.id,
                            'fiscal_position_id': partner.property_account_position_id.id,
                            'company_id': order.company_id.id,
                            'user_id': self.env.user.id,
                            'of_is_cee': True,
                        }
                        invoice = self.env['account.invoice'].create(invoice_vals)
                        references[invoice] = order
                        invoices[group_key] = invoice
                        invoices_origin[group_key] = [invoice.origin]
                        invoices_name[group_key] = [invoice.name]
                    elif group_key in invoices:
                        if order.name not in invoices_origin[group_key]:
                            invoices_origin[group_key].append(order.name)
                        if order.client_order_ref and order.client_order_ref not in invoices_name[group_key]:
                            invoices_name[group_key].append(order.client_order_ref)

                    # Create invoice line
                    account = cee_line.product_id.property_account_income_id or \
                        cee_line.product_id.categ_id.property_account_income_categ_id
                    if not account:
                        raise UserError(
                            u"Veuillez définir un compte de revenu pour cet article : \"%s\" (id. : %d) - "
                            u"ou pour sa catégorie \"%s\"" %
                            (cee_line.product_id.name, cee_line.product_id.id, cee_line.product_id.categ_id.name))

                    fpos = partner.property_account_position_id
                    if fpos:
                        account = fpos.map_account(account)

                    invoice_line_vals = {
                        'name': u"%s - %s - %s - %s" %
                                (order.name, order.partner_id.name, order.of_cee_number or u"Numéro CEE non renseigné",
                                 fields.Date.from_string(order.date_order).strftime('%d/%m/%Y')),
                        'origin': order.name,
                        'account_id': account.id,
                        'price_unit': abs(cee_line.price_unit),
                        'quantity': abs(cee_line.product_uom_qty),
                        'discount': cee_line.discount,
                        'uom_id': cee_line.product_uom.id,
                        'product_id': cee_line.product_id.id or False,
                        'invoice_line_tax_ids': [(6, 0, cee_line.tax_id.ids)],
                        'account_analytic_id': order.project_id.id,
                        'analytic_tag_ids': [(6, 0, cee_line.analytic_tag_ids.ids)],
                        'invoice_id': invoices[group_key].id,
                        'sale_line_ids': [(6, 0, [cee_line.id])],
                    }
                    self.env['account.invoice.line'].create(invoice_line_vals)

                    if references.get(invoices.get(group_key)):
                        if order not in references[invoices[group_key]]:
                            references[invoice] = references[invoice] | order

        for group_key in invoices:
            invoices[group_key].write({'name': ', '.join(invoices_name[group_key]),
                                       'origin': ', '.join(invoices_origin[group_key])})

        for invoice in invoices.values():
            invoice.compute_taxes()
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view(
                'mail.message_origin_link', values={'self': invoice, 'origin': references[invoice]},
                subtype_id=self.env.ref('mail.mt_note').id)

        # View invoices
        invoice_ids = map(lambda inv: inv.id, invoices.values())
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoice_ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoice_ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
