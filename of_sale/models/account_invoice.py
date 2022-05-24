# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_compare
import json


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ["account.invoice", "of.documents.joints"]

    @api.model
    def _of_function_active_picking(self):
        """
        Fonction appelée lors de la mise à jour du module.
        Détermine l'activation de la vue liée aux bons de livraison dans le formulaire des factures.
        """
        view = self.env.ref('of_sale.of_account_invoice_picking_view_form')
        if view:
            view.write({
                'active': self.env['ir.values'].get_default('account.config.settings', 'of_validate_pickings') in (2, 3)
                })

    of_date_vt = fields.Date(string="Date visite technique")
    of_sale_order_ids = fields.Many2many('sale.order', compute="_compute_of_sale_order_ids", string="Bons de commande")
    of_residual = fields.Float(
        string=u"Somme du montant non payé des factures d'acompte et de la facture finale",
        compute="_compute_of_residual")
    of_residual_equal = fields.Boolean(compute="_compute_of_residual")
    of_suivi_interne = fields.Char(string="Suivi interne")
    of_is_locked = fields.Boolean(compute="_compute_of_is_locked")
    of_waiting_delivery = fields.Boolean(string="Livraison en attente", compute="_compute_of_picking_ids")
    of_picking_ids = fields.Many2many('stock.picking', compute='_compute_of_picking_ids')
    of_picking_count = fields.Integer(string="Bon de livraisons", compute='_compute_of_picking_ids')
    of_price_printing = fields.Selection([
        ('order_line', u'Prix par ligne de commande'),
        ], string=u"Impressions des prix", default='order_line', required=True)

    @api.depends('invoice_line_ids')
    def _compute_of_sale_order_ids(self):
        for invoice in self:
            invoice.of_sale_order_ids = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')

    @api.depends('invoice_line_ids')
    def _compute_of_residual(self):
        group_paiements = self.env['of.invoice.report.total.group'].get_group_paiements()
        if not group_paiements.invoice:
            # Si le groupe des paiements est désactivé on ne gère pas les acomptes
            group_paiements = group_paiements.browse([])
        products = group_paiements.product_ids
        if group_paiements.categ_ids:
            products |= self.env['product.product'].search([('categ_id', 'in', group_paiements.categ_ids._ids)])
        if not products:
            for invoice in self:
                invoice.of_residual = invoice.residual
                invoice.of_residual_equal = True
            return
        for invoice in self:
            lines = invoice.invoice_line_ids.filtered(lambda l: l.product_id in products)
            if not lines:
                invoice.of_residual = invoice.residual
                invoice.of_residual_equal = True
                continue
            order_lines = lines.mapped('sale_line_ids')
            invoices = invoice | order_lines.mapped('invoice_lines').mapped('invoice_id')
            invoice.of_residual = sum(invoices.mapped('residual'))
            invoice.of_residual_equal = invoice.state == 'draft' or \
                                        float_compare(invoice.of_residual, invoice.residual, 2) == 0

    @api.depends('invoice_line_ids', 'invoice_line_ids.of_is_locked')
    def _compute_of_is_locked(self):
        for invoice in self:
            if invoice.invoice_line_ids == invoice.invoice_line_ids.filtered('of_is_locked'):
                invoice.of_is_locked = True

    @api.multi
    @api.depends('invoice_line_ids', 'invoice_line_ids.sale_line_ids', 'invoice_line_ids.sale_line_ids.order_id',
                 'invoice_line_ids.sale_line_ids.order_id.picking_ids')
    def _compute_of_picking_ids(self):
        """
        Calcule le nombre de BL liés à la facture.
        :return:
        """
        for invoice in self:
            pickings = invoice.of_sale_order_ids.mapped('picking_ids')
            if pickings:
                invoice.of_waiting_delivery = pickings.filtered(lambda p: p.state not in ['draft', 'cancel', 'done']) \
                                              and True or False
                invoice.of_picking_ids = pickings
                invoice.of_picking_count = len(pickings)

    @api.multi
    def validate_pickings(self):
        transfer_obj = self.env['stock.immediate.transfer']
        for invoice in self.filtered(lambda i: not i.of_is_locked):
            pickings = invoice.of_picking_ids
            # force_assign() ne fonctionne pas bien si des articles sont déjà considérés comme fait
            pickings.pack_operation_product_ids.write({'qty_done': 0.0})
            pickings.force_assign()
            for picking in pickings:
                new_transfer = transfer_obj.create({'pick_id': picking.id})
                new_transfer.process()
        self._compute_of_picking_ids()

    def get_color_section(self):
        return self.env['ir.values'].get_default('account.config.settings', 'of_color_bg_section')

    def get_color_font(self):
        return self.env['ir.values'].get_default('account.config.settings', 'of_color_font') or "#000000"

    @api.multi
    def action_invoice_open(self):
        """Mise à jour des dates de l'échéancier"""
        res = super(AccountInvoice, self).action_invoice_open()
        acompte_categ_id = self.env['ir.values'].get_default(
            'sale.config.settings', 'of_deposit_product_categ_id_setting')
        lines = self.mapped('invoice_line_ids').filtered(lambda line: line.product_id.categ_id.id != acompte_categ_id)
        orders = lines.mapped('sale_line_ids').mapped('order_id')
        orders.of_update_dates_echeancier()
        if self.env['ir.values'].get_default('account.config.settings', 'of_validate_pickings') == 3:
            self.validate_pickings()
        return res

    @api.multi
    def action_view_delivery(self):
        """
        Afficher les BL liés à la facture
        :return:
        """
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('of_picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    @api.multi
    def _of_get_linked_invoices(self):
        """ [IMPRESSION]
        Retourne les factures liées à la facture courante.
        Les factures liées sont celles dont une ligne est liée à la même ligne de commande qu'une ligne de lines.
        Toute facture liée à une facture liée est également retournée.
        """
        invoice_obj = self.env['account.invoice']
        self.ensure_one()
        if self.type != 'out_invoice':
            return self
        group_paiements = self.env['of.invoice.report.total.group'].get_group_paiements()
        if not (group_paiements and group_paiements.invoice):
            # Le groupe des paiements n'est pas coniguré pour les factures.
            return self

        group_paiements_lines = group_paiements.filter_lines(self.invoice_line_ids, self)
        if group_paiements_lines is False:
            # Aucune ligne de la facture n'est à considérer comme un paiement.
            return self

        invoices = self
        to_check = (group_paiements_lines
                    .mapped('sale_line_ids')
                    .mapped('invoice_lines')
                    .mapped('invoice_id')
                    .filtered(lambda i: i.state != 'cancel'))
        while to_check:
            invoices |= to_check
            to_check = (to_check
                        .mapped('invoice_line_ids')
                        .mapped('sale_line_ids')
                        .mapped('invoice_lines')
                        .mapped('invoice_id')
                        .filtered(lambda i: i.state != 'cancel')) - invoices

        refunds = invoices.filtered(lambda inv: inv.type != self.type)
        invoices -= refunds
        for refund in refunds:
            # On fait abstraction des factures annulées par des avoirs
            move_ids = refund.payment_move_line_ids.mapped('move_id')
            if len(move_ids) == 1:
                invoice = invoices.filtered(
                    lambda inv: inv.move_id == move_ids and inv.amount_total == refund.amount_total)
                if invoice:
                    if invoice == self:
                        # La facture en cours est annulée par un avoir
                        return self
                    invoices -= invoice

        # On ne garde que les factures dont toutes les lignes sont contrebalancées
        order_lines = invoices.mapped('invoice_line_ids').mapped('sale_line_ids')
        while order_lines:
            invs_to_remove = invoice_obj
            for order_line in order_lines:
                invs = order_line.invoice_lines.mapped('invoice_id').filtered(lambda inv: inv in invoices)
                if len(invs) == 1 and invs != self:
                    invs_to_remove |= invs
            invoices -= invs_to_remove
            order_lines = invs_to_remove.mapped('invoice_line_ids').mapped('sale_line_ids')

        # Tri dans l'ordre
        invoices = invoice_obj.search([('id', 'in', invoices.ids)])
        return invoices

    @api.multi
    def _of_get_printable_payments(self):
        """ [IMPRESSION]
        Renvoie les lignes à afficher.
        """
        account_move_line_obj = self.env['account.move.line']

        # Retour de tous les paiements des factures
        # On distingue les paiements de la facture principale de ceux des factures liées
        result_dict = {}
        for invoice in self:
            widget = json.loads(invoice.payments_widget.replace("'", "\'"))
            if not widget:
                continue
            for payment in widget.get('content', []):
                # Les paiements sont classés dans l'ordre chronologique
                sort_key = (payment['date'], invoice.date_invoice, invoice.number, payment['payment_id'])
                move_line = account_move_line_obj.browse(payment['payment_id'])
                name = self._of_get_payment_display(move_line)
                result_dict[sort_key] = (name, payment['amount'])
        result = [result_dict[key] for key in sorted(result_dict)]
        return result

    @api.multi
    def _of_get_recap_taxes(self, invoices):
        """ [IMPRESSION]
        Retourne la liste des taxes à afficher dans le récapitulatif de la facture pdf.
        """
        tax_vals = []
        taxes = {}
        round_curr = self.currency_id.round
        inv_type = self.type
        for inv in invoices:
            sign = inv.type == inv_type or -1
            for inv_tax in inv.tax_line_ids:
                tax = inv_tax.tax_id
                if tax in taxes:
                    vals = taxes[tax]
                    vals[1] += inv_tax.base * sign
                    vals[2] += inv_tax.amount * sign
                else:
                    vals = [tax.description, inv_tax.base * sign, inv_tax.amount * sign]
                    tax_vals.append(vals)
                    taxes[tax] = vals
        for vals in tax_vals:
            vals[1] = round_curr(vals[1])
            vals[2] = round_curr(vals[2])
        return [vals for vals in tax_vals if vals[1]]

    @api.multi
    def of_get_printable_data(self):
        result = super(AccountInvoice, self).of_get_printable_data()
        report_pages_full = self.order_lines_layouted()
        report_lines = result['lines']
        report_pages = []
        for page_full in report_pages_full:
            page = []
            for group in page_full:
                lines = [line for line in group['lines'] if line in report_lines]
                if lines:
                    group['lines'] = lines
                    page.append(group)
            if page:
                report_pages.append(page)
        result['lines_layouted'] = report_pages
        return result

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Surcharge pour que tout avoir soit pris en compte dans la commande
        """
        result = super(AccountInvoice, self)._refund_cleanup_lines(lines)
        if self.env.context.get('of_mode') == 'cancel':
            for i in xrange(0, len(lines)):
                for name, field in lines[i]._fields.iteritems():
                    if name == 'sale_line_ids':
                        result[i][2][name] = [(6, 0, lines[i][name].ids)]
        return result

    def pdf_vt_pastille(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_vt_pastille')

    @api.model
    def _get_invoice_line_key_cols(self):
        field_list = super(AccountInvoice, self)._get_invoice_line_key_cols()
        field_list.append('layout_category_id')
        return field_list


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    price_unit = fields.Float(digits=False)
    of_is_locked = fields.Boolean(compute="_compute_is_locked", string=u"Article particulier")

    @api.model
    def get_locked_category_ids(self):
        """
        Fait dans une fonction pour faciliter l'héritage.
        :return: Ids des catégories dont le montant des articles ne doit pas changer des bons de commandes
        """
        return [self.env['ir.values'].get_default('sale.config.settings',
                                                  'of_deposit_product_categ_id_setting')]

    @api.model
    def get_locked_product_ids(self):
        """
        Fait dans une fonction pour faciliter l'héritage.
        :return: Ids des articles qui ne doivent pas être supprimés des bons de commandes
        """
        return []

    @api.depends('product_id')
    def _compute_is_locked(self):
        """
        of_is_locked est un champ qui permet de savoir si une ligne de facture doit empêcher sa contrepartie sur bon
        de commande d'être supprimée (voir sale.order.line.unlink())
        """
        locked_category_ids = self.get_locked_category_ids()
        locked_product_ids = self.get_locked_product_ids()
        for invoice_line in self:
            if invoice_line.product_id.categ_id.id not in locked_category_ids and \
                    invoice_line.product_id.id not in locked_product_ids:
                invoice_line.of_is_locked = False
            else:
                invoice_line.of_is_locked = True

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        afficher_descr_fab = self.env.user.company_id.afficher_descr_fab
        afficher = afficher_descr_fab == 'factures' or afficher_descr_fab == 'devis_factures'
        product = self.product_id.with_context(
            lang=self.invoice_id.partner_id.lang,
            partner=self.invoice_id.partner_id.id,
            )
        if product and product.description_fabricant and afficher:
            self.name += '\n' + product.description_fabricant
        return res

    @api.multi
    def write(self, vals):
        fields_to_sync = {
            'price_unit': 'price_unit',
            'uom_id': 'product_uom',
            'discount': 'discount',
            'of_discount_formula': 'of_discount_formula',
            'invoice_line_tax_ids': 'tax_id'
            }
        res = super(AccountInvoiceLine, self).write(vals)
        if res:
            for line in self.filtered('of_is_locked'):
                if line.invoice_id.invoice_line_ids.filtered('of_is_locked') == line.invoice_id.invoice_line_ids \
                        and len(line.sale_line_ids) == 1 and line.sale_line_ids.invoice_lines == line:
                    sync = [x for x in fields_to_sync.keys() if x in vals.keys()]
                    vals_order_line = {}
                    for field in sync:
                        vals_order_line[fields_to_sync[field]] = vals[field]
                    line.sale_line_ids.with_context(force_price=True).write(vals_order_line)
        return res


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    @api.model
    def _get_of_option_date(self):
        result = super(AccountPaymentTermLine, self)._get_of_option_date()
        for i in xrange(len(result)):
            if result[i][0] == 'invoice':
                i += 1
                break
        return result[:i] + [('order', 'Date de commande')] + result[i:]

