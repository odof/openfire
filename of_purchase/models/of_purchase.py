# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_expected = fields.Char(string='Livraison attendue', states={'done': [('readonly', True)]})
    purchase_ids = fields.One2many("purchase.order", "sale_order_id", string="Achats")
    purchase_count = fields.Integer(compute='_compute_purchase_count')
    of_user_id = fields.Many2one(comodel_name='res.users', string="Responsable technique")

    @api.depends('purchase_ids')
    @api.multi
    def _compute_purchase_count(self):
        for sale_order in self:
            sale_order.purchase_count = len(sale_order.purchase_ids)

    @api.multi
    def action_view_achats(self):
        action = self.env.ref('of_purchase.of_purchase_open_achats').read()[0]
        action['domain'] = [('sale_order_id', 'in', self._ids)]
        return action


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    customer_id = fields.Many2one('res.partner', string='Client')
    sale_order_id = fields.Many2one('sale.order', string="Commande d'origine")
    delivery_expected = fields.Char(string='Livraison attendue', states={'done': [('readonly', True)]})
    of_sent = fields.Boolean(string=u"CF envoyée")
    of_project_id = fields.Many2one(comodel_name='account.analytic.account', string=u"Compte analytique")
    of_user_id = fields.Many2one(comodel_name='res.users', string="Responsable technique")

    @api.model
    def _prepare_picking(self):
        values = super(PurchaseOrder, self)._prepare_picking()
        return isinstance(values, dict) and values.update({'of_customer_id': self.customer_id.id}) or values

    @api.multi
    def button_confirm(self):
        procurement_obj = self.env['procurement.order']
        super(PurchaseOrder, self).button_confirm()
        if self.env['ir.values'].get_default('sale.config.settings', 'of_recalcul_pa'):
            for line in self.order_line:
                procurements = procurement_obj.search([('purchase_line_id', '=', line.id)])
                moves = procurements.mapped('move_dest_id')
                sale_lines = moves.mapped('procurement_id').mapped('sale_line_id')
                sale_lines.write({'of_seller_price': line.price_unit,
                                  'purchase_price': line.price_unit * line.product_id.property_of_purchase_coeff})


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        if 'price_unit' in vals:
            # On répercute le changement de prix pour la valorisation de l'inventaire s'il y a lieu
            moves = self.mapped('move_ids')
            if moves:
                moves.write({'price_unit': vals['price_unit']})
                quants = moves.mapped('quant_ids')
                if quants:
                    quants.sudo().write({'cost': vals['price_unit']})
        return res


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _prepare_purchase_order(self, partner):
        res = super(ProcurementOrder, self)._prepare_purchase_order(partner)
        sale_order = self.env['sale.order'].browse(self._context.get('purchase_sale_order_id', False))

        res['customer_id'] = self._context.get('purchase_customer_id', False) or sale_order.partner_id.id
        res['sale_order_id'] = sale_order.id
        res['delivery_expected'] = sale_order.delivery_expected
        res['of_project_id'] = sale_order.project_id.id
        if sale_order.of_user_id:
            res['of_user_id'] = sale_order.of_user_id.id

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

            # Si trouvée, prendre la description de la ligne de commande
            # et ajouter éventuellement la description du produit
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
        if not sale_order:
            sale_order = self.move_dest_id.picking_id.sale_id

        return sale_order

    @api.multi
    def make_po(self):
        cache = {}
        res = []
        for procurement in self:
            suppliers = procurement.product_id.seller_ids.filtered(
                lambda r: not r.product_id or r.product_id == procurement.product_id)
            if not suppliers:
                procurement.message_post(
                    body=(_('No vendor associated to product %s. Please set one to fix this procurement.')
                          % procurement.product_id.name))
                continue
            supplier = procurement._make_po_select_supplier(suppliers)
            partner = supplier.name

            # Recherche du client associé
            domain = ()
            # @TODO: Récupérer le type de regroupement sélectionné en configuration
            #   ('standard', 'sale_order', 'customer') à implémenter
            regroup_type = 'sale_order'
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
                if regroup_type == 'sale_order':
                    proc = procurement.with_context(purchase_sale_order_id=sale_order and sale_order.id)
                elif regroup_type == 'customer':
                    proc = procurement.with_context(purchase_customer_id=sale_order and sale_order.partner_id.id)
                else:
                    proc = procurement

                vals = proc._prepare_purchase_order(partner)
                po = self.env['purchase.order'].create(vals)
                name = (procurement.group_id and (procurement.group_id.name + ":") or "")\
                    + (procurement.name != "/" and procurement.name or "")
                message = _("This purchase order has been created from: "
                            "<a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
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
                name = (self.group_id and (self.group_id.name + ":") or "") + (self.name != "/" and self.name or "")
                message = _("This purchase order has been modified from: "
                            "<a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
                po.message_post(body=message)
            if po:
                res += [procurement.id]

            # Create Line
            po_line = False
            separate_lines = self.env['ir.values'].sudo().get_default(
                'purchase.config.settings', 'of_description_as_order_setting')
            if not separate_lines:
                for line in po.order_line:
                    if line.product_id == procurement.product_id\
                            and line.product_uom == procurement.product_id.uom_po_id:
                        procurement_uom_po_qty = procurement.product_uom._compute_quantity(
                            procurement.product_qty, procurement.product_id.uom_po_id)
                        seller = procurement.product_id._select_seller(
                            partner_id=partner,
                            quantity=line.product_qty + procurement_uom_po_qty,
                            date=po.date_order and po.date_order[:10],
                            uom_id=procurement.product_id.uom_po_id)

                        price_unit = self.env['account.tax']._fix_tax_included_price(
                            seller.price, line.product_id.supplier_taxes_id, line.taxes_id) if seller else 0.0
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

    of_description_as_order_setting = fields.Selection(
        [(0, 'Description article telle que saisie dans le catalogue'),
         (1, 'Description article telle que saisie dans le devis')],
        string="(OF) Description articles",
        help=u"Choisissez le type de description affiché dans la commande fournisseur.\n"
             u"Cela affecte également les documents imprimables.")

    @api.multi
    def set_description_as_order_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'purchase.config.settings', 'of_description_as_order_setting', self.of_description_as_order_setting)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_customer_id = fields.Many2one('res.partner', string="Client")
    # Permet de cacher le champ of_customer_id si pas sur BR
    of_location_usage = fields.Selection(related="location_id.usage")
    of_user_id = fields.Many2one(comodel_name='res.users', string="Responsable technique")


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if isinstance(res, dict):
            responsable = self.procurement_id.sale_line_id.order_id.of_user_id
            if responsable:
                res['of_user_id'] = responsable.id
        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_br_count = fields.Integer(string=u"Réceptions", compute="compute_br_count")

    def compute_br_count(self):
        picking_obj = self.env['stock.picking']
        for partner in self:
            partner.of_br_count = picking_obj.search_count(
                [('of_customer_id', '=', partner.id), ('of_location_usage', '=', 'supplier')])

    @api.multi
    def action_view_picking(self):
        action = self.env.ref('of_purchase.of_purchase_open_picking').read()[0]
        action['domain'] = [('of_customer_id', 'in', self._ids)]
        return action


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_recalcul_pa = fields.Boolean(string=u"(OF) Recalcul auto des prix d'achats sur lignes de commande")

    @api.multi
    def set_of_recalcul_pa_defaults(self):
        return self.env['ir.values'].sudo().set_default(
                'sale.config.settings', 'of_recalcul_pa', self.of_recalcul_pa)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_cr_context
    def _auto_init(self):
        model = self.env['ir.model'].search([('model', '=', self._name)])
        fields_obj = self.env['ir.model.fields']
        standard_price_field = fields_obj.search([('model_id', '=', model.id), ('name', '=', 'standard_price')])
        purchase_coeff_field = fields_obj.search([('model_id', '=', model.id), ('name', '=', 'property_of_purchase_coeff')])
        test = self.env['ir.config_parameter'].get_param('property_of_purchase_coeff_generated', False)

        res = super(ProductProduct, self)._auto_init()
        if not test:
            if not purchase_coeff_field:
                purchase_coeff_field = fields_obj.search([('model_id', '=', model.id), ('name', '=', 'property_of_purchase_coeff')])
            if purchase_coeff_field:
                self.env['ir.config_parameter'].set_param('property_of_purchase_coeff_generated', 'True')
                self.env.cr.execute("DELETE FROM ir_property WHERE name = 'standard_price' AND res_id LIKE 'product.product,%' AND SUBSTRING(res_id FROM 17)::integer NOT IN (SELECT id FROM product_product);")
                self.env.cr.execute("""
INSERT INTO ir_property (
    create_uid,
    create_date,
    write_uid,
    write_date,
    name,
    value_float,
    res_id,
    company_id,
    fields_id,
    type
)
(
    SELECT  1
    ,       now()
    ,       1
    ,       now()
    ,       'property_of_purchase_coeff'
    ,       CASE WHEN IP.value_float = 0 THEN
                1
            ELSE
                (IP.value_float / COALESCE( (   SELECT      PS.price
                                                FROM        product_supplierinfo    PS
                                                ,           product_product         PP
                                                WHERE       PP.id                   = CAST(SUBSTRING(res_id FROM POSITION(',' IN res_id) + 1) AS INT)
                                                AND         PS.product_tmpl_id      = PP.product_tmpl_id
                                                AND         PS.price                > 0
                                                ORDER BY    PS.sequence
                                                ,           PS.min_qty DESC
                                                ,           PS.price
                                                LIMIT 1
                                            ), IP.value_float)
                )
            END
    ,       IP.res_id
    ,       IP.company_id
    ,       %s
    ,       'float'
    FROM    ir_property IP
    WHERE   IP.name = 'standard_price'
    AND     IP.fields_id = %s
)
;
""", (purchase_coeff_field.id, standard_price_field.id))
        return res

    property_of_purchase_coeff = fields.Float(string="Coefficient d'achat", company_dependent=True)

    @api.multi
    def of_propage_cout(self, cout):
        super(ProductProduct, self).of_propage_cout(cout)
        self.of_purchase_coeff_cost_propagation(cout)

    @api.multi
    def of_purchase_coeff_cost_propagation(self, cost):
        # Le coefficient d'achat (property_of_purchase_coeff) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env['res.company'].search(['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        property_obj = self.env['ir.property'].sudo()
        coeff_values = {product.id: cost and product.of_seller_price and cost / product.of_seller_price or 1
                        for product in self}
        for company in companies:
            property_obj.with_context(force_company=company.id).set_multi(
                'property_of_purchase_coeff', 'product.product', coeff_values)

    @api.multi
    def of_purchase_coeff_seller_price_propagation(self, seller_price):
        # Le coefficient d'achat (property_of_purchase_coeff) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env['res.company'].search(['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        property_obj = self.env['ir.property'].sudo()
        coeff_values = {product.id: product.standard_price and seller_price and product.standard_price / seller_price
                        or 1 for product in self}
        for company in companies:
            property_obj.with_context(force_company=company.id).set_multi(
                'property_of_purchase_coeff', 'product.product', coeff_values)


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.multi
    def write(self, vals):
        if 'price' in vals and len(self) == 1:
            price = vals['price']
            product_tmpl_id = vals.get('product_tmpl_id', self.product_tmpl_id.id)
            product_id = vals.get('product_id', self.product_id.id)
            products_done = self.env['product.product']

            if product_tmpl_id:
                product_tmpl = self.env['product.template'].browse(product_tmpl_id)
                if product_tmpl.seller_ids and product_tmpl.seller_ids[0].id == self.id:
                    product_tmpl.product_variant_ids.of_purchase_coeff_seller_price_propagation(price)
                    products_done |= product_tmpl.product_variant_ids

            if product_id and (not products_done or product_id not in products_done.ids):
                product = self.env['product.product'].browse(product_id)
                if product.seller_ids and product.seller_ids[0].id == self.id:
                    product.of_purchase_coeff_seller_price_propagation(price)
        return super(ProductSupplierinfo, self).write(vals)
