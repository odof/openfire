# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_worktop_configurator_order = fields.Boolean(string=u"Devis issu du calculateur")
    of_submitted_worktop_configurator_order = fields.Boolean(string=u"Devis soumis issu du calculateur")
    of_worktop_configurator_internal_vendor = fields.Boolean(string=u"Réalisé par HM Déco")
    of_worktop_configurator_internal_code = fields.Char(string=u"Code interne", compute='_compute_internal_code')
    of_worktop_configurator_discount_id = fields.Many2one(
        comodel_name='of.worktop.configurator.discount', string=u"Remise")
    of_delivery_floor = fields.Integer(string=u"Étage de livraison")
    of_site_service_id = fields.Many2one(
        comodel_name='of.worktop.configurator.service', string=u"Prestations du chantier")
    of_junction = fields.Boolean(string=u"Raccordement")

    def _compute_internal_code(self):
        for order in self.filtered(lambda o: o.of_worktop_configurator_order):
            discount_product_id = self.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_discount_product_id')
            if discount_product_id:
                order_lines = order.order_line.filtered(lambda l: l.product_id.id != discount_product_id)
            else:
                order_lines = order.order_line
            diff = sum(order.order_line.mapped(lambda l: l.price_unit * l.product_uom_qty)) - \
                sum(order_lines.mapped(lambda l: l.of_no_coef_price * l.product_uom_qty))
            order.of_worktop_configurator_internal_code = u"CDI%05d" % int(diff)

    @api.multi
    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        for line in self.order_line:
            line.price_unit = line.of_no_coef_price * line.get_pricelist_coef()
        self._compute_internal_code()

    @api.multi
    def write(self, vals):
        super(SaleOrder, self).write(vals)
        # Gestion de la remise en cas de modification de la remise ou de la liste de prix
        if 'of_worktop_configurator_discount_id' in vals or 'pricelist_id' in vals:
            discount_product_id = self.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_discount_product_id')
            if discount_product_id:
                for order in self.filtered(lambda o: o.of_worktop_configurator_order):
                    # On supprime la ligne de remise si elle est déjà présente
                    order.order_line.filtered(lambda l: l.product_id.id == discount_product_id).unlink()
                    # On traite la nouvelle remise
                    if order.of_worktop_configurator_discount_id:
                        # On calcul le prix de la remise
                        discount_price = -order.amount_untaxed * \
                                         (order.of_worktop_configurator_discount_id.value / 100.0)
                        # On ajoute la ligne de remise
                        order_line = self.env['sale.order.line'].create(
                            {'order_id': order.id,
                             'product_id': discount_product_id,
                             'product_uom_qty': 1.0})
                        order_line.product_id_change()
                        order_line.price_unit = discount_price
                        order_line.of_no_coef_price = order_line.price_unit
                        order_line.price_unit = order_line.price_unit * order_line.get_pricelist_coef()
                        order_line._compute_tax_id()
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_worktop_configurator_weight = fields.Float(string=u"Poids de la pièce (kg)")
    of_no_coef_price = fields.Float(
        string=u"Prix sans coefficient", required=True, digits=dp.get_precision('Product Price'), default=0.0)

    def get_pricelist_coef(self):
        """
        Permet de récupérer le coefficient de la liste de prix à appliquer au prix de la ligne
        """
        if self.product_id:
            items = self.order_id.pricelist_id.item_ids.filtered(
                lambda i: i.applied_on == '0_product_variant' and i.product_id.id == self.product_id.id and
                i.compute_price == 'coef')
            if not items:
                items = self.order_id.pricelist_id.item_ids.filtered(
                    lambda i: i.applied_on == '1_product' and
                    i.product_tmpl_id.id == self.product_id.product_tmpl_id.id and i.compute_price == 'coef')
            if not items:
                items = self.order_id.pricelist_id.item_ids.filtered(
                    lambda i: i.applied_on == '2_product_category' and i.categ_id.id == self.product_id.categ_id.id and
                    i.compute_price == 'coef')
            if not items:
                items = self.order_id.pricelist_id.item_ids.filtered(
                    lambda i: i.applied_on == '2.5_brand' and i.of_brand_id.id == self.product_id.brand_id.id and
                    i.compute_price == 'coef')
            if not items:
                items = self.order_id.pricelist_id.item_ids.filtered(
                    lambda i: i.applied_on == '3_global' and i.compute_price == 'coef')
            return items and items[0].of_coef or 1.0
        return 1.0


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_website_worktop_configurator_fiscal_position_ids = fields.Many2many(
        comodel_name='account.fiscal.position', string=u"(OF) Positions fiscales")
    of_website_worktop_configurator_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term', string=u"(OF) Condition de règlement")
    of_website_worktop_configurator_extra_floor_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article supplément livraison à l'étage")
    of_website_worktop_configurator_extra_service_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article supplément prestation")
    of_website_worktop_configurator_extra_junction_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article supplément raccordement")
    of_website_worktop_configurator_extra_weight_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article supplément poids")
    of_website_worktop_configurator_discount_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article remise")
    of_website_worktop_configurator_acc_layout_category_id = fields.Many2one(
        comodel_name='sale.layout_category', string=u"(OF) Section de devis pour les accessoires et prestations")
    of_website_worktop_configurator_extra_layout_category_id = fields.Many2one(
        comodel_name='sale.layout_category', string=u"(OF) Section de devis pour les suppléments")

    @api.multi
    def set_of_website_worktop_configurator_fiscal_position_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_fiscal_position_ids',
            self.of_website_worktop_configurator_fiscal_position_ids.ids)

    @api.multi
    def set_of_website_worktop_configurator_payment_term_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_payment_term_id',
            self.of_website_worktop_configurator_payment_term_id.id)

    @api.multi
    def set_of_website_worktop_configurator_extra_floor_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_floor_product_id',
            self.of_website_worktop_configurator_extra_floor_product_id.id)

    @api.multi
    def set_of_website_worktop_configurator_extra_service_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_service_product_id',
            self.of_website_worktop_configurator_extra_service_product_id.id)

    @api.multi
    def set_of_website_worktop_configurator_extra_junction_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_junction_product_id',
            self.of_website_worktop_configurator_extra_junction_product_id.id)

    @api.multi
    def set_of_website_worktop_configurator_extra_weight_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_weight_product_id',
            self.of_website_worktop_configurator_extra_weight_product_id.id)

    @api.multi
    def set_of_website_worktop_configurator_discount_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_discount_product_id',
            self.of_website_worktop_configurator_discount_product_id.id)

    @api.multi
    def set_of_website_worktop_configurator_acc_layout_category_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_acc_layout_category_id',
            self.of_website_worktop_configurator_acc_layout_category_id.id)

    @api.multi
    def set_of_website_worktop_configurator_extra_layout_category_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_layout_category_id',
            self.of_website_worktop_configurator_extra_layout_category_id.id)

