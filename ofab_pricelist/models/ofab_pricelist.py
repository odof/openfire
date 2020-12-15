# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from itertools import chain
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    of_coef_usage = fields.Boolean(string='Utilisation des coefficients')

    @api.multi
    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        """ Fonction reprise du module product et qui doit être remplacée
        pour modifier la requête sql pour rechercher sur les marques
        """
        self.ensure_one()
        if not date:
            date = self._context.get('date') or fields.Date.context_today(self)
        if not uom_id and self._context.get('uom'):
            uom_id = self._context['uom']
        if uom_id:
            # rebrowse with uom if given
            products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
            products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in enumerate(products_qty_partner)]
        else:
            products = [item[0] for item in products_qty_partner]
 
        if not products:
            return {}
 
        categ_ids = {}
        brand_ids = {}  # Modification Openfire
        for p in products:
            categ = p.categ_id
            brand_ids[p.brand_id.id] = True  # Modification Openfire
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = categ_ids.keys()
        brand_ids = brand_ids.keys()  # Modification Openfire
 
        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]
 
        # Load all rules
        # Début modifications Openfire
        self._cr.execute(
            'SELECT item.id '
            'FROM product_pricelist_item AS item '
            'LEFT JOIN product_category AS categ '
            'ON item.categ_id = categ.id '
            'WHERE (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))'
            'AND (item.product_id IS NULL OR item.product_id = any(%s))'
            'AND (item.categ_id IS NULL OR item.categ_id = any(%s)) '
            'AND (item.of_brand_id IS NULL OR item.of_brand_id = any(%s)) '
            'AND (item.pricelist_id = %s) '
            'AND (item.date_start IS NULL OR item.date_start<=%s) '
            'AND (item.date_end IS NULL OR item.date_end>=%s)'
            'ORDER BY item.applied_on, item.min_quantity desc, categ.parent_left desc',
            (prod_tmpl_ids, prod_ids, categ_ids, brand_ids, self.id, date, date))
        # Fin modifications Openfire

        item_ids = [x[0] for x in self._cr.fetchall()]
        items = self.env['product.pricelist.item'].browse(item_ids)
        results = {}
        for product, qty, partner in products_qty_partner:
            results[product.id] = 0.0
            suitable_rule = False
 
            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = self._context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = self.env['product.uom'].browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass
 
            # if Public user try to access standard price from website sale, need to call price_compute.
            # TDE SURPRISE: product can actually be a template
            price = product.price_compute('list_price')[product.id]
 
            price_uom = self.env['product.uom'].browse([qty_uom_id])
            for rule in items:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue
 
                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                # Début modifications Openfire
                if rule.of_brand_id and rule.of_brand_id.id != product.brand_id.id:
                    continue
                # Fin modifications Openfire

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price_tmp = rule.base_pricelist_id._compute_price_rule([(product, qty, partner)])[product.id][0]  # TDE: 0 = price, 1 = rule
                    price = rule.base_pricelist_id.currency_id.compute(price_tmp, self.currency_id, round=False)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_compute returns the price in the context UoM, i.e. qty_uom_id
                    price = product.price_compute(rule.base)[product.id]
 
                convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom))
 
                if price is not False:
                    if rule.compute_price == 'fixed':
                        price = convert_to_price_uom(rule.fixed_price)
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price / 100))) or 0.0
                    else:
                        # complete formula
                        price_limit = price
                        price = (price - (price * (rule.price_discount / 100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)
 
                        if rule.price_surcharge:
                            price_surcharge = convert_to_price_uom(rule.price_surcharge)
                            price += price_surcharge
 
                        if rule.price_min_margin:
                            price_min_margin = convert_to_price_uom(rule.price_min_margin)
                            price = max(price, price_limit + price_min_margin)
 
                        if rule.price_max_margin:
                            price_max_margin = convert_to_price_uom(rule.price_max_margin)
                            price = min(price, price_limit + price_max_margin)
                    suitable_rule = rule
                break
            # Final price conversion into pricelist currency
            if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                price = product.currency_id.compute(price, self.currency_id, round=False)
 
            results[product.id] = (price, suitable_rule and suitable_rule.id or False)
 
        return results

class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    of_coef = fields.Float(string=u"Coefficient")
    of_brand_id = fields.Many2one('of.product.brand', string="Marque")
    applied_on = fields.Selection(selection_add=[('2.5_brand', 'Marque')])
    compute_price = fields.Selection(selection_add=[('coef', 'Coefficient')])

    @api.onchange('applied_on')
    def _onchange_applied_on(self):
        """ Vide le champ 'of_brand_id' si nécessaire
        """
        super(ProductPricelistItem, self)._onchange_applied_on()
        if self.applied_on != '2.5_brand':
            self.of_brand_id = False

    @api.onchange('compute_price')
    def _onchange_compute_price(self):
        """ Vide le champ 'of_coef' si nécessaire
        """
        super(ProductPricelistItem, self)._onchange_compute_price()
        if self.compute_price != 'coef':
            self.of_coef = 0.0

    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge', 'of_brand_id', 'of_coef')
    def _get_pricelist_item_name_price(self):
        """ surcharge de la fonction du module product pour modifier
        le calcul des champs 'name' et 'price' afin de calculer
        les nouvelles sélections des champs 'applied_on' et 'compute_price'
        """
        super(ProductPricelistItem, self)._get_pricelist_item_name_price()
        if self.of_brand_id:
            self.name = 'Marque : ' + self.of_brand_id.name

        if self.compute_price == 'coef':
            self.price = "prix d'achat x %s = prix de vente" % (self.of_coef)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_coef = fields.Float(string="Coefficient", help=u"Permet de calculer le prix de vente", compute="_get_coef", store=True)
    of_coef_usage = fields.Boolean(string="Utilisation du coefficient", compute="_get_of_coef_usage")

    @api.depends('pricelist_id')
    def _get_of_coef_usage(self):
        for order in self:
            order.of_coef_usage = self.pricelist_id and self.pricelist_id.of_coef_usage

    @api.depends('pricelist_id', 'partner_id')
    def _get_coef(self):
        """ Permet de récupérer le premier coefficient global de la lsite de prix
        """
        for order in self:
            items = order.pricelist_id.item_ids.filtered(lambda i: i.applied_on == '3_global' and i.compute_price == 'coef')
            if items:
                order.of_coef = items[0].of_coef
            else:
                order.of_coef = 1.00

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Récupération de valeurs par défaut via la vue xml 'ofab_pricelist_view_order_form'
    of_coef = fields.Float(string="Coefficient", help=u"Permet de calculer le prix de vente")
    of_coef_usage = fields.Boolean(string="Utilisation des coefficients")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        """ Permet de recalculer le prix si le coefficient est utilisé
        """
        res = super(SaleOrderLine, self).product_id_change()
        if self.of_coef_usage:
            if self.product_id:
                items = self.order_id.pricelist_id.item_ids.filtered(lambda i: i.applied_on == '0_product_variant' and i.product_id.id == self.product_id.id and i.compute_price == 'coef')
                if not items:
                    items = self.order_id.pricelist_id.item_ids.filtered(lambda i: i.applied_on == '1_product' and i.product_tpl_id.id == self.product_id.product_tpl_id.id and i.compute_price == 'coef')
                if not items:
                    items = self.order_id.pricelist_id.item_ids.filtered(lambda i: i.applied_on == '2_product_category' and i.categ_id.id == self.product_id.categ_id.id and i.compute_price == 'coef')
                if not items:
                    items = self.order_id.pricelist_id.item_ids.filtered(lambda i: i.applied_on == '2.5_brand' and i.of_brand_id.id == self.product_id.brand_id.id and i.compute_price == 'coef')
                self.of_coef = items and items[0].of_coef or self.of_coef
            self.product_uom_change()
        return res

    @api.onchange('product_uom_qty', 'product_uom')
    def product_uom_change(self):
        super(SaleOrderLine, self).product_uom_change()
        if self.of_coef_usage:
            factor = self.product_uom and self.product_uom.factor_inv or 1
            if self.of_is_kit:
                self.price_unit = (self.kit_id and self.kit_id.cost_comps or 0) * self.of_coef * factor
            else:
                purchase_factor = self.product_id and self.product_id.uom_po_id and self.product_id.uom_po_id.factor \
                                  or 1
                if self.env['ir.values'].get_default('sale.config.settings', 'of_coef_method') == 'cost':
                    self.price_unit = self.purchase_price * self.of_coef * factor * purchase_factor
                else:
                    self.price_unit = (self.product_id and self.product_id.of_seller_price or 0) * self.of_coef * \
                                      factor * purchase_factor

    @api.onchange('of_coef', 'product_id.of_seller_price', 'purchase_price')
    def onchange_of_coef(self):
        """ Permet de recalculer le prix si le coefficient est utilisé 
        et que le coefficient, le prix d'achat ou le coût est modifié
        """
        if self.of_coef_usage:
            self.product_uom_change()

    @api.onchange('of_coef_usage')
    def onchange_of_coef_usage(self):
        """ Permet de recalculer le prix si on décide d'utiliser le coefficient ou non
        """
        if self.of_coef_usage:
            self.product_uom_change()
        if not self.of_coef_usage and self.product_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_coef_method = fields.Selection(
        selection=[('purchase', u"Applique le coefficient sur le prix d'achat de l'article"),
                   ('cost', u"Applique le coefficient sur le coût de l'article")],
        string=u"(OF) Utilisation du coefficient", required=True, default='purchase')

    @api.multi
    def set_of_coef_method_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_coef_method', self.of_coef_method)
