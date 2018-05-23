# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_expected = fields.Char(string='Livraison attendue', states={'done': [('readonly', True)]})

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    customer_id = fields.Many2one('res.partner', string='Client')
    sale_order_id = fields.Many2one('sale.order', string="Commande d'origine")
    delivery_expected = fields.Char(string='Livraison attendue', states={'done': [('readonly', True)]})

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

#    order_id = fields.Many2one('sale.order', related='sale_line_id.order_id')

    @api.multi
    def _prepare_purchase_order(self, partner):
        res = super(ProcurementOrder, self)._prepare_purchase_order(partner)
        sale_order_id = self._context.get('purchase_sale_order_id', False)
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id)

        res['customer_id'] = self._context.get('purchase_customer_id', False) or (sale_order_id and sale_order.partner_id.id)
        res['sale_order_id'] = sale_order_id
        res['delivery_expected'] = sale_order_id and sale_order.delivery_expected

        return res

    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        """
        Prendre la description de la ligne de commande et ajouter la description du produit
        """
        res = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)

        # Option : Description articles
        desc_option = self.env['ir.values'].get_default('purchase.config.settings', 'of_description_as_order_setting')

        if desc_option:
            # recherche d'une ligne de commande associee
            sale_line = self.sale_line_id
            if not sale_line:
                # Si non trouvée, remonter la chaine des stock.move
                move = self.move_dest_id
                sale_line = move and move.procurement_id and move.procurement_id.sale_line_id

            # Si trouvée, prendre la description de la ligne de commande et ajouter éventuellement la description du produit
            if sale_line:
                name = sale_line.display_name
                product_lang = self.product_id.with_context({
                    'lang': supplier.name.lang,
                    'partner_id': supplier.name.id,
                })
                if product_lang.description_purchase:
                    name += '\n' + product_lang.description_purchase
                res["name"] = name
        return res

    def _get_sale_order(self):
        self.ensure_one()
        sale_line = self.sale_line_id
        if not sale_line:
            move = self.move_dest_id
            sale_line = move and move.procurement_id and move.procurement_id.sale_line_id
        sale_order = sale_line and sale_line.order_id or False
        return sale_order

    @api.multi
    def make_po(self):
        cache = {}
        res = []
        for procurement in self:
            suppliers = procurement.product_id.seller_ids.filtered(lambda r: not r.product_id or r.product_id == procurement.product_id)
            if not suppliers:
                procurement.message_post(body=_('No vendor associated to product %s. Please set one to fix this procurement.') % (procurement.product_id.name))
                continue
            supplier = procurement._make_po_select_supplier(suppliers)
            partner = supplier.name

            # Recherche du client associé
            domain = ()
            regroup_type = 'sale_order'  #@TODO: Récupérer le type de regroupement sélectionné en configuration ('standard', 'sale_order', 'customer') à implémenter
            if regroup_type != 'standard':
                sale_order = procurement._get_sale_order()
                if regroup_type == 'sale_order':
                    domain = (('sale_order_id', '=', sale_order and sale_order.id),)
                elif regroup_type == 'customer':
                    domain = (('customer', '=', sale_order and sale_order.partner_id.id),)

            gpo = procurement.rule_id.group_propagation_option
            group = (gpo == 'fixed' and procurement.rule_id.group_id) or \
                    (gpo == 'propagate' and procurement.group_id) or False

            domain += (
                ('partner_id', '=', partner.id),
                ('state', '=', 'draft'),
                ('picking_type_id', '=', procurement.rule_id.picking_type_id.id),
                ('company_id', '=', procurement.company_id.id),
                ('dest_address_id', '=', procurement.partner_dest_id.id))
            if group:
                domain += (('group_id', '=', group.id),)

            if domain in cache:
                po = cache[domain]
            else:
                po = self.env['purchase.order'].search([dom for dom in domain])
                po = po[0] if po else False
                cache[domain] = po
            if not po:
                proc = procurement

                if regroup_type == 'sale_order':
                    proc = procurement.with_context(purchase_sale_order_id=sale_order and sale_order.id)
                elif regroup_type == 'customer':
                    proc = procurement.with_context(purchase_customer_id=sale_order and sale_order.partner_id.id)
                else:
                    proc = procurement

                vals = proc._prepare_purchase_order(partner)
                po = self.env['purchase.order'].create(vals)
                name = (procurement.group_id and (procurement.group_id.name + ":") or "") + (procurement.name != "/" and procurement.name or procurement.move_dest_id.raw_material_production_id and procurement.move_dest_id.raw_material_production_id.name or "")
                message = _("This purchase order has been created from: <a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
                po.message_post(body=message)
                cache[domain] = po
            elif not po.origin or procurement.origin not in po.origin.split(', '):
                # Keep track of all procurements
                if po.origin:
                    if procurement.origin:
                        po.write({'origin': po.origin + ', ' + procurement.origin})
                    else:
                        po.write({'origin': po.origin})
                else:
                    po.write({'origin': procurement.origin})
                name = (self.group_id and (self.group_id.name + ":") or "") + (self.name != "/" and self.name or self.move_dest_id.raw_material_production_id and self.move_dest_id.raw_material_production_id.name or "")
                message = _("This purchase order has been modified from: <a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
                po.message_post(body=message)
            if po:
                res += [procurement.id]

            # Create Line
            po_line = False
            for line in po.order_line:
                if line.product_id == procurement.product_id and line.product_uom == procurement.product_id.uom_po_id:
                    procurement_uom_po_qty = procurement.product_uom._compute_quantity(procurement.product_qty, procurement.product_id.uom_po_id)
                    seller = procurement.product_id._select_seller(
                        partner_id=partner,
                        quantity=line.product_qty + procurement_uom_po_qty,
                        date=po.date_order and po.date_order[:10],
                        uom_id=procurement.product_id.uom_po_id)

                    price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, line.product_id.supplier_taxes_id, line.taxes_id) if seller else 0.0
                    if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
                        price_unit = seller.currency_id.compute(price_unit, po.currency_id)

                    po_line = line.write({
                        'name': line.name,
                        'product_qty': line.product_qty + procurement_uom_po_qty,
                        'price_unit': price_unit,
                        'procurement_ids': [(4, procurement.id)]
                    })
                    break
            if not po_line:
                vals = procurement._prepare_purchase_order_line(po, supplier)
                self.env['purchase.order.line'].create(vals)
        return res

# Ajouter la configuration "Description articles"
class OFPurchaseConfiguration(models.TransientModel):
    _inherit = 'purchase.config.settings'

    of_description_as_order_setting = fields.Selection([
        (0, 'Description article telle que saisie dans le catalogue'),
        (1, 'Description article telle que saisie dans le devis')
        ], "(OF) Description articles",
        help="Choisissez le type de description affiché dans la commande fournisseur.\n Cela affecte également les documents imprimables.")

    @api.multi
    def set_description_as_order_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'purchase.config.settings', 'of_description_as_order_setting', self.of_description_as_order_setting)
