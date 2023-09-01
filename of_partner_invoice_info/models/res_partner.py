# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_invoice_balance_total = fields.Monetary(
        compute='_compute_of_invoice_balance_total', string=u"Montant facturé dû",)
    of_sale_order_to_invoice_amount = fields.Monetary(
        compute='_compute_of_sale_order_to_invoice_amount', string=u"Montant à facturer")

    # Champs ajoutés pour recherche dans les filtres personnalisés
    of_is_to_invoice = fields.Boolean(
        compute=lambda s: None, search='_search_of_is_to_invoice', string=u"Commandes à facturer")
    of_has_unpaid_invoice = fields.Boolean(
        compute=lambda s: None, search='_search_of_has_unpaid_invoice', string=u"Factures à payer")

    @api.depends()
    def _compute_of_invoice_balance_total(self):
        # Fonction copiée de la fonction res.partner._invoice_total() du module account
        account_invoice_report = self.env['account.invoice.report']
        if not self.ids:
            self.total_invoiced = 0.0
            return True

        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self:
            # price_total is in the company currency
            all_partners_and_children[partner] = self.with_context(active_test=False).search(
                [('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        # searching account.invoice.report via the orm is comparatively expensive
        # (generates queries "id in []" forcing to build the full table).
        # In simple cases where all invoices are in the same currency as the user's company
        # access directly these elements

        # generate where clause to include multicompany rules
        where_query = account_invoice_report._where_calc([
            ('partner_id', 'in', all_partner_ids), ('state', 'not in', ['draft', 'cancel']),
            ('type', 'in', ('out_invoice', 'out_refund'))
        ])
        account_invoice_report._apply_ir_rules(where_query, 'read')
        from_clause, where_clause, where_clause_params = where_query.get_sql()

        # price_total is in the company currency
        query = """
            SELECT SUM(residual) as total, partner_id
            FROM account_invoice_report account_invoice_report
            WHERE %s
            GROUP BY partner_id
            """ % where_clause
        self.env.cr.execute(query, where_clause_params)
        price_totals = self.env.cr.dictfetchall()
        for partner, child_ids in all_partners_and_children.items():
            partner.of_invoice_balance_total = sum(
                price['total'] for price in price_totals if price['partner_id'] in child_ids)

    def _compute_of_sale_order_to_invoice_amount(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        sale_order_groups = self.env['sale.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids), ('invoice_status', '=', 'to invoice')],
            fields=['partner_id', 'amount_total'], groupby=['partner_id']
        )
        for group in sale_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.of_sale_order_to_invoice_amount += group['amount_total']
                partner = partner.parent_id

    @api.model
    def _search_of_is_to_invoice(self, operator, value):
        op = '=' if (operator == '=') == value else '!='
        return [('sale_order_ids.invoice_status', op, 'to invoice')]

    @api.model
    def _search_of_has_unpaid_invoice(self, operator, value):
        op = 'in' if (operator == '=') == value else 'not in'
        invoices = self.env['account.invoice'].search([('type', '=', 'out_invoice'), ('state', '=', 'open')])
        return [('id', op, invoices.mapped('partner_id').ids)]
