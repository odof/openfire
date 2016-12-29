# -*- coding: utf-8 -*-

from openerp import models, api
from main import MAGIC_COLUMNS_VALUES, MAGIC_COLUMNS_TABLES

class import_sale(models.AbstractModel):
    _inherit = 'of.migration'

    @api.model
    def import_sale_order(self):
        cr = self._cr

        # Association des sale_order_61 aux nouveaux sale_order 9.0
        cr.execute("UPDATE sale_order_61 SET id_90 = nextval('sale_order_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['origin', 'client_order_ref', 'date_order', 'partner_id', 'amount_untaxed', 'company_id', 'note', 'state',
                     'pricelist_id', 'project_id', 'amount_tax', 'payment_term_id', 'partner_invoice_id', 'user_id',
                     'fiscal_position_id', 'amount_total', 'name', 'partner_shipping_id'] #, 'invoice_status', 'validity_date'

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'                 : 'tab.id_90',
            'partner_id'         : 'partner.id_90',
            'company_id'         : 'shop.id_90',
            # Mapping de state confirmé par OpenUpgrade
            'state'              : "CASE WHEN tab.state IN ('waiting_date', 'progress', 'manual', 'shipping_except', 'invoice_except') THEN 'sale' ELSE tab.state END",
            'pricelist_id'       : 'pricelist.id_90',
            'project_id'         : 'project.id_90',
            'payment_term_id'    : 'payment_term.id_90',
            'partner_invoice_id' : 'partner_invoice.id_90',
            'user_id'            : 'res_user.id_90',
            'fiscal_position_id' : 'fiscal_position.id_90',
#             'invoice_status'     : normalement recalculé automatiquement après sale.order.line._get_invoice_qty,
            'partner_shipping_id': 'partner_shipping.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'sale_order_61', False, False, False),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('shop', 'sale_shop_61', 'id', 'tab', 'shop_id'),
            ('pricelist', 'product_pricelist_61', 'id', 'tab', 'pricelist_id'),
            ('project', 'account_analytic_account_61', 'id', 'tab', 'project_id'),
            ('payment_term', 'account_payment_term_61', 'id', 'tab', 'payment_term'),
            ('partner_invoice', 'res_partner_address_61', 'id', 'tab', 'partner_invoice_id'),
            ('res_user', 'res_users_61', 'id', 'tab', 'user_id'),
            ('fiscal_position', 'account_fiscal_position_61', 'id', 'tab', 'fiscal_position'),
            ('partner_shipping', 'res_partner_address_61', 'id', 'tab', 'partner_shipping_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('sale.order', values, tables)

    @api.model
    def import_sale_order_line(self):
        cr = self._cr

        # Association des sale_order_61 aux nouveaux sale_order 9.0
        cr.execute("UPDATE sale_order_line_61 SET id_90 = nextval('sale_order_line_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['sequence', 'price_unit', 'product_uom_qty', 'currency_id', 'product_uom', 'customer_lead', 'company_id', 'name',
                     'state', 'order_partner_id', 'order_id', 'discount', 'qty_delivered', 'product_id', 'salesman_id', 'project_id']
                    #'qty_to_invoice', 'qty_invoiced', 'price_tax', 'price_subtotal', 'price_reduce', 'price_total','invoice_status'

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'              : 'tab.id_90',
#             'qty_to_invoice'  : normalement recalculé automatiquement après _get_invoice_qty,
#             'qty_invoiced'    : fonction _get_invoice_qty,
            'currency_id'     : 'pricelist_90.currency_id',
            'product_uom'     : 'uom.id_90',
            'customer_lead'   : 'tab.delay',
#             'price_tax'       : fonction _compute_amount,
            'company_id'      : 'order_90.company_id',
            'state'           : 'order_90.state',
            'order_partner_id': 'order_90.partner_id',
            'order_id'        : 'sale_order.id_90',
#             'price_subtotal'  : fonction _compute_amount,
#             'price_reduce'    : normalement recalculé automatiquement après _compute_amount,
            'qty_delivered'   : '0', # @todo: champ a calculer ...
#             'price_total'     : fonction _compute_amount,
#             'invoice_status'  : normalement recalculé automatiquement après _get_invoice_qty,
            'product_id'      : 'product.id_90',
            'salesman_id'     : 'salesman.id_90',
            'project_id'      : 'NULL',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'sale_order_line_61', False, False, False),
            ('sale_order', 'sale_order_61', 'id', 'tab', 'order_id'),
            ('order_90', 'sale_order', 'id', 'sale_order', 'id_90'),
            ('pricelist_90', 'product_pricelist', 'id', 'sale_order', 'pricelist_id'),
            ('product', 'product_product_61', 'id', 'tab', 'product_id'),
            ('uom', 'product_uom_61', 'id', 'tab', 'product_uom'),
            ('salesman', 'res_users_61', 'id', 'tab', 'salesman_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('sale.order.line', values, tables)


        # Ajout du lien lignes de commande - lignes de factures
        cr.execute("INSERT INTO sale_order_line_invoice_rel(order_line_id, invoice_line_id)\n"
                   "SELECT o.id_90, i.id_90\n"
                   "FROM sale_order_invoice_rel_61 AS rel\n"
                   "INNER JOIN sale_order_line_61 AS o ON o.order_id = rel.order_id\n"
                   "INNER JOIN account_invoice_line_61 AS i ON i.invoice_id = rel.invoice_id\n"
                   "WHERE o.product_id = i.product_id")

        # Ajout des relations de taxes
        self._cr.execute("INSERT INTO account_tax_sale_order_line_rel(sale_order_line_id, account_tax_id)\n"
                         "SELECT rel1.id_90, rel2.id_90\n"
                         "FROM sale_order_tax_61 AS tab\n"
                         "INNER JOIN sale_order_line_61 AS rel1 ON rel1.id = tab.order_line_id\n"
                         "INNER JOIN account_tax_61 AS rel2 ON rel2.id = tab.tax_id\n"
                         "WHERE rel1.id_90 IS NOT NULL\n"
                         "  AND rel2.id_90 IS NOT NULL")

        # Mise à jour des champs calculés
        lines = self.env['sale.order.line'].search([])
        lines._compute_amount()
        lines._get_invoice_qty()

        # la mise a jour des montants du bon de commande se fait automatiquement à la mise à jour du total ttc 
        #   (price_total) de la ligne de commande
        # Cependant, lors de l'appel à lines._compute_amount, le total ttc de la ligne peut etre attribué avant son total de taxe,
        #   ce qui fausse le calcul dans le bon de commande. On le recalcule donc une deuxième fois ici
        orders = self.env['sale.order'].search([])
        orders._amount_all()

    @api.model
    def import_procurement_order(self):
        cr = self._cr

        # Association des procurement_order_61 aux nouveaux procurement_order 9.0
        cr.execute("UPDATE procurement_order_61 SET id_90 = nextval('procurement_order_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['origin', 'product_id', 'product_uom', 'date_planned', 'message_last_post', 'company_id', 'priority',
                     'state', 'product_qty', 'rule_id', 'group_id', 'name', 'sale_line_id', 'task_id']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'               : 'tab.id_90',
            'product_id'       : 'product.id_90',
            'product_uom'      : 'uom.id_90',
            'message_last_post': 'NULL',
            'company_id'       : 'COALESCE(shop.id_90, comp.id_90)',
            'rule_id'          : 000,
            'group_id'         : 000,
            'sale_line_id'     : 000,
            'task_id'          : 000,
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'sale_order_61', False, False, False),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('sale.order', values, tables)


    @api.model
    def import_module_sale(self):
        return (
            'sale_order',
            'sale_order_line',
#             'procurement_order', # @todo : Migrer la partie approvisionnement
        )
