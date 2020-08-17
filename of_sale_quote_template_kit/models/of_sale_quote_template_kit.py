# -*- coding: utf-8 -*-


from odoo import api, fields, models
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp

class OfSaleorderKit(models.Model):
    _inherit = 'of.saleorder.kit'

    # Ajout du champ pour permettre l'utilisation des kits dans les sale.quote.line
    quote_line_id = fields.Many2one('sale.quote.line', string='quote line')

    @api.model
    def _clear_db(self):
        not_linked = self.search([('order_line_id', '=', False), ('quote_line_id', '=', False)])
        kits_to_link = self.env['sale.order.line'].search([('kit_id', 'in', not_linked._ids)])
        for kit in kits_to_link:
            kit.kit_id.order_line_id = kit.id
            not_linked -= kit.kit_id
        not_linked.unlink()


class SaleQuoteLine(models.Model):
    _inherit = "sale.quote.line"
    _description = u"Lignes de modèle de devis"
    _order = 'sequence, id'

    kit_id = fields.Many2one('of.saleorder.kit', string="Composants", copy=True)
    of_is_kit = fields.Boolean(string='Est un kit')

    price_comps = fields.Float(
        string='Prix comp/Kit', compute='_compute_price_comps',  # digits=dp.get_precision('Product Price'),
        help="Sum of the prices of all components necessary for 1 unit of this kit",)

    of_pricing = fields.Selection(
        [
            ('fixed', u'Fixé'),
            ('computed', u'Calculé'),
        ], string="Tarification", required=True, default='fixed',
        help="This field is only relevant if the product is a kit. It represents the way the price should be computed.\n"
             "if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit.\n"
             "if set to 'computed', the price will be computed according to the components of the kit.")

    sale_kits_to_unlink = fields.Boolean(string="sale kits to unlink?", default=False, help="True if at least 1 sale kit needs to be deleted from database")

    @api.depends('kit_id.kit_line_ids')
    def _compute_price_comps(self):
        """ Permet de calculer les prix des composants
        """
        for line in self:
            if line.kit_id:
                line.price_comps = line.kit_id.price_comps
                line.cost_comps = line.kit_id.cost_comps

    @api.onchange('price_comps', 'of_pricing', 'product_id')
    def _refresh_price_unit(self):
        """ Permet de recalculer le prix de vente du kit en fonction du type de prix
        """
        for line in self:
            if line.of_is_kit:
                if line.of_pricing == 'computed':
                    line.price_unit = line.price_comps

    @api.onchange('of_pricing')
    def _onchange_of_pricing(self):
        """ Permet de lancer le recalcul du prix de vente du kit
        """
        self.ensure_one()
        if self.of_pricing:
            if self.kit_id:
                self.kit_id.write({'of_pricing': self.of_pricing})
                self._refresh_price_unit()

    @api.onchange('of_is_kit')
    def _onchange_of_is_kit(self):
        """ Fonction qui permet de créer un kit directement en ligne de modèle
        """
        new_vals = {}
        if self.kit_id:  # former product was a kit -> unlink it's kit_id
            self.kit_id.write({"to_unlink": True})
            new_vals["kit_id"] = False
            new_vals["sale_kits_to_unlink"] = True
        if self.of_is_kit:  # checkbox got checked
            if not self.product_id.of_is_kit:  # a product that is not a kit is being made into a kit
                # we create a component with current product (for procurements, kits are ignored)
                new_comp_vals = {
                    'product_id': self.product_id.id,
                    'name': self.product_id.name_get()[0][1] or self.product_id.name,
                    'qty_per_kit': 1,
                    'product_uom_id': self.product_uom_id.id or self.product_id.uom_id.id,
                    'price_unit': self.product_id.list_price,
                    'cost_unit': self.product_id.standard_price,
                    'customer_lead': self.product_id.sale_delay,
                    'hide_prices': False,
                    }
                sale_kit_vals = {
                    'of_pricing': 'computed',
                    'kit_line_ids': [(0, 0, new_comp_vals)],
                    }
                new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)
                new_vals["of_pricing"] = "computed"
            else:  # can happen if uncheck then recheck a kit
                new_vals['of_pricing'] = self.product_id.of_pricing
                sale_kit_vals = self.product_id.get_saleorder_kit_data()
                new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)

        else:  # a product that was a kit is not anymore, we unlink its components
            new_vals["of_pricing"] = 'fixed'
            new_vals["price_unit"] = self.product_id.list_price
        self.update(new_vals)
        self._refresh_price_unit()

    @api.onchange('kit_id')
    def _onchange_kit_id(self):
        """ Permet le recalcul du prix total des composants et du prix de vente
        si le kit change
        """
        self.ensure_one()
        if self.kit_id:
            self._compute_price_comps()
            self._refresh_price_unit()

    @api.model
    def create(self, vals):
        """ À voir avec Cédric pour confirmer l'effet
        """
        if vals.get("sale_kits_to_unlink"):
            self.env["of.saleorder.kit"].search([("to_unlink", "=", True)]).unlink()
            vals.pop("sale_kits_to_unlink")
        line = super(SaleQuoteLine, self).create(vals)
        sale_kit_vals = {'quote_line_id': line.id, 'name': line.name, 'of_pricing': line.of_pricing}
        line.kit_id.write(sale_kit_vals)
        return line

    @api.multi
    def write(self, vals):
        """ À voir avec Cédric pour confirmer l'effet
        """
        if vals.get("sale_kits_to_unlink") or self.sale_kits_to_unlink:
            self.env["of.saleorder.kit"].search([("to_unlink", "=", True)]).unlink()
            vals["sale_kits_to_unlink"] = False
        update_ol_id = False
        if len(self) == 1 and vals.get("kit_id") and not self.kit_id:
            # a sale_order_kit was added
            update_ol_id = True
        elif len(self) == 1 and vals.get("name") and self.kit_id:
            # line changed name
            update_ol_id = True
        elif 'of_pricing' in vals:
            update_ol_id = True
        if len(self) == 1 and ((self.of_pricing == 'computed' and not vals.get('of_pricing')) or vals.get('of_pricing') == 'computed'):
            vals['price_unit'] = vals.get('price_comps', self.price_comps)  # price_unit is equal to price_comps if pricing is computed
        super(SaleQuoteLine, self).write(vals)
        if update_ol_id:
            sale_kit_vals = {'quote_line_id': self.id}
            if vals.get("name"):
                sale_kit_vals["name"] = vals.get("name")
            if vals.get("of_pricing"):
                sale_kit_vals["of_pricing"] = vals.get("of_pricing")
            self.kit_id.write(sale_kit_vals)
        return True

    @api.multi
    def copy_data(self, default=None):
        """ La duplication d'une ligne de commande implique la duplication de son kit
        """
        res = super(SaleQuoteLine, self).copy_data(default)
        if res[0].get('kit_id'):
            res[0]['kit_id'] = self.kit_id.copy().id
        return res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ permet de récupérer les valeurs du produit
        """
        res = super(SaleQuoteLine, self)._onchange_product_id()
        new_vals = {}
        if self.kit_id:  # former product was a kit -> unlink it's kit_id
            self.kit_id.write({"to_unlink": True})
            new_vals['kit_id'] = False
            new_vals["sale_kits_to_unlink"] = True
        if self.product_id.of_is_kit:  # new product is a kit, we need to add its components
            new_vals['of_is_kit'] = True
            new_vals['of_pricing'] = self.product_id.of_pricing
            sale_kit_vals = self.product_id.get_saleorder_kit_data()
            sale_kit_vals["qty_order_line"] = self.product_uom_qty
            new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)
        else:  # new product is not a kit
            new_vals['of_is_kit'] = False
            new_vals['of_pricing'] = 'fixed'
        self.update(new_vals)
        return res

    @api.onchange('product_uom_id')
    def _onchange_product_uom(self):
        """ Permet de recalculer le prix des kits si on change l'udm
        """
        super(SaleQuoteLine, self)._onchange_product_uom()
        if self.product_id and self.product_uom_id:
            self._refresh_price_unit()

    def get_saleorder_kit_data(self):
        self.ensure_one()
        if not self.of_is_kit:
            return {}
        res = {'of_pricing': self.of_pricing}
        lines = [(5,)]
        comp_vals = {}
        if self.of_pricing == 'fixed':
            comp_vals["hide_prices"] = True
        kit = self.kit_id
        for line in kit.kit_line_ids:
            comp_vals = comp_vals.copy()
            comp_vals["product_id"] = line.product_id.id
            comp_vals["product_uom_id"] = line.product_uom_id.id
            comp_vals["qty_per_kit"] = line.qty_per_kit
            comp_vals["sequence"] = line.sequence
            comp_vals["name"] = line.product_id.name_get()[0][1] or line.product_id.name
            comp_vals["price_unit"] = line.product_id.list_price
            comp_vals["cost_unit"] = line.product_id.standard_price
            comp_vals["customer_lead"] = line.product_id.sale_delay
            lines.append((0, 0, comp_vals))
        res["kit_line_ids"] = lines
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_data_from_template(self, line, price, discount):
        """ Permet d'ajouter les données liées aux kits dnas les lignes de commande
        """
        data = super(SaleOrder, self)._get_data_from_template(line, price, discount)
        sale_kit_vals = line.get_saleorder_kit_data()
        sale_kit_vals["qty_order_line"] = line.product_uom_qty
        new_vals = self.env["of.saleorder.kit"].create(sale_kit_vals)
        data.update({
            'kit_id' : new_vals,
            'of_is_kit' : line.of_is_kit,
            'price_comps' : line.price_comps,
            'of_pricing' : line.of_pricing,
            'sale_kits_to_unlink' : line.sale_kits_to_unlink,
        })
        return data

    def _compute_prices_from_template(self):
        """ Permet de recalculer le prix des lignes de commande qui sont des kits
        """
        super(SaleOrder, self)._compute_prices_from_template()
        self.order_line._refresh_price_unit()
