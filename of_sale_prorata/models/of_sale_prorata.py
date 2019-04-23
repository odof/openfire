# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_default_of_product_prorata_id(self, cr, uid, context):
        product_obj = self.env['product.product']
        products = product_obj.search([('default_code', 'ilike', 'prorata')])
        if not products:
            products = product_obj.search([('name', 'ilike', 'prorata')])
        return products and products[0] or False

    of_prorata_percent = fields.Float(string='Charges compte prorata(%)', digits=(4, 5))
    of_retenue_garantie_pct = fields.Float(
        string='Retenue de garantie(%)', digits=(4, 5),
        help=u"Retenue calculée depuis le montant total de la commande")
    of_prochaine_situation = fields.Integer(
        compute='_compute_of_prochaine_situation', string="Prochaine situation",
        help=u"Situation pour laquelle la prochaine facture sera générée")
    of_nb_situations = fields.Integer(string="Nb. situations")

    @api.depends()
    def _compute_of_prochaine_situation(self):
        product_situation_id = self.env['ir.values'].get_default('sale.config.settings', 'of_product_situation_id_setting')
        for order in self:
            n = 1
            if product_situation_id:
                for invoice in order.invoice_ids:
                    if invoice.state == 'cancel':
                        continue
                    if invoice.invoice_line_ids and invoice.invoice_line_ids[0].product_id.id == product_situation_id:
                        n += invoice.type == 'out_invoice' and 1 or -1
            order.of_prochaine_situation = n

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """ Ajout d'une ligne de prorata dans la facture générée """
        invoice_ids = super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)

        for order in self:
            if not order.of_prorata_percent:
                continue

            amount_untaxed = 0.0
            for line in order.order_line:
                if line.product_uom_qty:
                    amount_untaxed += line.price_subtotal

            for invoice in order.invoice_ids:
                if invoice.id in invoice_ids:
                    invoice.of_add_prorata_line(order.of_prorata_percent, base_amount=amount_untaxed)
                    # Pour le cas normalement impossible où on fait des factures groupées avec des comptes prorata, on évite de doubler l'opération
                    invoice_ids.remove(invoice.id)
                    break
        return invoice_ids

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_retenue_garantie_pct'] = self.of_retenue_garantie_pct
        return invoice_vals

    @api.multi
    def of_button_situation(self):
        self.ensure_one()
        wizard_obj = self.env['of.wizard.situation']
        product_situation_id = self.env['ir.values'].get_default('sale.config.settings', 'of_product_situation_id_setting')
        if not product_situation_id:
            raise UserError(u"Vous devez définir l'Article de situation dans la configuration des ventes.")
        situation_data = {
            'order_id': self.id,
            'line_ids': [(0, 0, {'order_line_id': line.id}) for line in self.order_line
                         if line.product_uom_qty or line.situation_ids],
        }
        wizard = wizard_obj.create(situation_data)

        action = {
            'type'     : 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.wizard.situation',
            'res_id'   : wizard.id,
        }
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    situation_ids = fields.One2many('of.sale.order.line.situation', 'order_line_id', string='Lignes de situation')


class SaleOrderLineSituation(models.Model):
    _name = 'of.sale.order.line.situation'
    _order = 'order_id DESC, order_line_id DESC, situation'

    order_id = fields.Many2one('sale.order', related='order_line_id.order_id', readonly=True)
    order_line_id = fields.Many2one('sale.order.line', string='Ligne de commande', readonly=True, required=True, ondelete='cascade')
    situation = fields.Integer(string='Situation', required=True)
    value = fields.Integer(u"Réalisation (%)")
    invoice_line_id = fields.Many2one('account.invoice.line', string='Ligne de facture', readonly=True)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)
        invoice_ids = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'), fields=['id'])
        if len(invoice_ids) == 1:
            invoice = self.env['account.invoice'].browse(invoice_ids[0]['id'])
            if invoice.of_retenue_garantie and invoice.residual > invoice.of_retenue_garantie:
                # Retrait de la retenue de garantie du montant à payer
                rec['amount'] = invoice.residual - invoice.of_retenue_garantie
            elif invoice.of_retenue_garantie:
                # Paiement de la retenue de garantie de la facture, mais aussi des factures de situation
                rec['amount'] = sum(invoice.of_sale_order_ids.mapped('invoice_ids').mapped('residual'))
        return rec


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_retenue_garantie = fields.Float(
        compute='_compute_of_retenue_garantie', digits=dp.get_precision('Product Price'),
        string='Retenue de garantie')
    of_retenue_garantie_pct = fields.Float(
        string='Retenue de garantie(%)', digits=(4, 5),
        help=u"Pourcentage appliqué sur le total TTC de la facture (après application des charges de compte de prorata)")

    @api.depends('of_retenue_garantie_pct', 'amount_total')
    def _compute_of_retenue_garantie(self):
        for invoice in self:
            invoice.of_retenue_garantie = invoice.currency_id.round(invoice.of_retenue_garantie_pct * invoice.amount_total * 0.01)

    @api.multi
    def of_add_prorata_line(self, pct, sale_order=False, base_amount=False):
        """ Ajoute une ligne de prorata à la facture.
        L'article de prorata est défini dans la configuration de vente et détermine la taxe qui sera utilisée.
        Normalement il s'agit toujours d'une charge taxée à 20%.
        @param order: Commande associée à la facture, pour ajout d'une ligne de commande
        @param amount : Si False, le montant sera le total hors taxes de la facture
        """
        self.ensure_one()
        if not pct:
            return
        if base_amount is False:
            base_amount = self.amount_untaxed
        if not base_amount:
            return
        order_line_obj = self.env['sale.order.line']
        invoice_line_obj = self.env['account.invoice.line']
        product_prorata_id = self.env['ir.values'].get_default('sale.config.settings', 'of_product_prorata_id_setting')
        if not product_prorata_id:
            raise UserError("Vous devez renseigner un article de prorata dans la configuration des ventes")
        product_prorata = self.env['product.product'].browse(product_prorata_id)

        product_prorata_name = product_prorata.name_get()[0][1]
        if product_prorata.description_sale:
            product_prorata_name += '\n' + product_prorata.description_sale
        # Utilisation des comptes/taxes à l'achat et non à la vente
        taxes = product_prorata.supplier_taxes_id.filtered(lambda r: r.company_id == self.company_id)
        taxes = self.fiscal_position_id.map_tax(taxes, product_prorata, self.partner_id)

        # Calcul du montant de prorata
        amount = pct * base_amount * -0.01
        amount = self.currency_id.round(amount)

        # --- Création de la ligne de commande si la commande est renseignée ---
        so_line = sale_order and order_line_obj.create({
            'name': product_prorata_name,
            'price_unit': amount,
            'product_uom_qty': 0.0,
            'order_id': sale_order.id,
            'discount': 0.0,
            'product_uom': product_prorata.uom_id.id,
            'product_id': product_prorata.id,
            'tax_id': [(6, 0, taxes._ids)],
        })

        # --- Création de la ligne de facture ---
        account = invoice_line_obj.get_invoice_line_account('in_invoice', product_prorata, self.fiscal_position_id, self.company_id)

        # Si le module of_account_tax est installé, on calcule le compte comptable en fonction des taxes
        if hasattr(taxes, 'map_account'):
            for tax in taxes:
                account = tax.map_account(account)

        inv_line = invoice_line_obj.create({
            'invoice_id': self.id,
            'name': product_prorata_name,
            'origin': sale_order and sale_order.name or False,
            'account_id': account.id,
            'price_unit': amount,
            'quantity': 1.0,
            'discount': 0.0,
            'uom_id': product_prorata.uom_id.id,
            'product_id': product_prorata.id,
            'sale_line_ids': so_line and [(6, 0, [so_line.id])] or [],
            'invoice_line_tax_ids': [(6, 0, taxes._ids)],
            'account_analytic_id': sale_order and sale_order.project_id.id or False,
        })
        inv_line.onchange_tax_ids()
        self.compute_taxes()

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        """ Modification des écritures comptables générées pour traiter la retenue de garantie.
        Ce code sert sert à extraire le montant de la retenue de garantie du compte 411 pour le placer dans
          le compte spécifié dans la configuration de la société (normalement le compte 4117).
        En raison de la complexité pour gérer ensuite la saisie des paiements à travers ces deux comptes,
          le code suivant a été désactivé. Seul le compte client (411) sera utilisé.
        """
        return super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)

        if not self.of_retenue_garantie_pct:
            return move_lines

    @api.multi
    def _of_get_printable_totals(self):
        result = super(AccountInvoice, self)._of_get_printable_totals()
        if self.of_retenue_garantie:
            total = False
            for line_type in ('total', 'taxes', 'subtotal'):
                if result[line_type]:
                    total = result[line_type][-1][1][1]
                    break

            invoices = self
            for group, lines in self._of_get_total_lines_by_group():
                if group and group.is_group_paiements():
                    # Liste des factures et factures d'acompte
                    invoices = self._of_get_linked_invoices(lines)
            retenue_garantie = sum(invoices.mapped('of_retenue_garantie'))

            round_curr = self.currency_id.round
            if total > retenue_garantie:
                # On retranche la retenue de garantie du montant à payer
                #  SAUF si il ne reste plus que la retenue de garantie à payer
                result['total'].append(
                    [
                        [("Retenue de garantie", round_curr(retenue_garantie))],
                        ["A payer", round_curr(total - retenue_garantie)]
                    ]
                )
        return result

class Company(models.Model):
    _inherit = 'res.company'

    of_journal_situation_id = fields.Many2one(
        'account.journal', compute='compute_of_journal_situation_id', string='Journal de situation')

    @api.depends()
    def compute_of_journal_situation_id(self):
        journal_obj = self.env['account.journal']
        for company in self:
            journal = journal_obj.search([('company_id', '=', company.id),
                                          ('type', '=', 'sale'),
                                          ('name', 'like', 'situation')], limit=1)
            if not journal:
                journal = journal_obj.search([('company_id', '=', company.id),
                                              ('type', '=', 'sale')], limit=1)
            company.of_journal_situation_id = journal


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_product_prorata_id_setting = fields.Many2one(
        'product.product',
        string=u"(OF) Article de prorata",
        help=u"Article utilisé pour le compte de prorata")

    of_product_situation_id_setting = fields.Many2one(
        'product.product',
        string=u"(OF) Article de situation",
        help=u"Article utilisé pour les factures de situation")

    @api.multi
    def set_of_product_prorata_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_product_prorata_id_setting', self.of_product_prorata_id_setting.id)

    @api.multi
    def set_of_product_situation_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_product_situation_id_setting', self.of_product_situation_id_setting.id)
