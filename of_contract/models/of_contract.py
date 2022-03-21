# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    of_amount_untaxed = fields.Monetary(string='Montant ht', compute='_compute_of_amount_all', store=True)
    of_amount_tax = fields.Monetary(string='Montant taxes', compute='_compute_of_amount_all', store=True)
    of_amount_total = fields.Monetary(string='Montant total', compute='_compute_of_amount_all', store=True)
    of_fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale")

    @api.depends('recurring_invoice_line_ids.price_subtotal', 'of_fiscal_position_id')
    def _compute_of_amount_all(self):
        # Code adapté de la fonction _amout_all définie dans le module sale pour sale.order
        for contract in self:
            currency = (
                contract.pricelist_id.currency_id or
                contract.partner_id.property_product_pricelist.currency_id or
                contract.company_id.currency_id
            )
            fpos = contract.of_fiscal_position_id

            amount_untaxed = amount_total = 0.0
            for line in contract.recurring_invoice_line_ids:

                taxes = line.product_id.taxes_id.filtered(lambda r: r.company_id == contract.company_id)
                line.tax_id = fpos.map_tax(taxes, line.product_id, contract.partner_id) if fpos else taxes
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                tax_amounts = line.tax_id.compute_all(
                    price, currency, line.quantity, product=line.product_id, partner=contract.partner_id)

                if contract.company_id.tax_calculation_rounding_method != 'round_globally':
                    tax_amounts['total_excluded'] = currency.round(tax_amounts['total_excluded'])
                    tax_amounts['total_included'] = currency.round(tax_amounts['total_included'])
                amount_untaxed += tax_amounts['total_excluded']
                amount_total += tax_amounts['total_included']

            contract.update({
                'of_amount_untaxed': currency.round(amount_untaxed),
                'of_amount_tax': currency.round(amount_total - amount_untaxed),
                'of_amount_total': currency.round(amount_total),
            })

    @api.multi
    def _prepare_invoice(self):
        res = super(AccountAnalyticAccount, self)._prepare_invoice()
        if self.of_fiscal_position_id:
            res['fiscal_position_id'] = self.of_fiscal_position_id.id
        return res

    @api.multi
    def _create_invoice(self):
        # A chaque création de facture un utilisateur est abonné et le cache est invalidé.
        # Si plusieurs contrats sont sélectionnés pour générer leur facture, il est donc coûteux de recalculer les
        # champs sur toutes les factures à chaque itération.
        # Ce code pourra être retiré à partir de la v12 car l'invalidation du cache sera plus précise.
        return super(AccountAnalyticAccount, self.with_prefetch())._create_invoice()

    @api.model
    def _prepare_invoice_line(self, line, invoice_id):
        # On force l'appel de onchange_tax_ids dans le cas où le module of_account_tax est installé
        # pour le recalcul correct des comptes
        return super(
            AccountAnalyticAccount,
            self.with_context(of_force_product_onchange_tax=True)
        )._prepare_invoice_line(line, invoice_id)
