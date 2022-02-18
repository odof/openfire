# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfSelectProductWizard(models.TransientModel):
    _name = 'of.select.product.wizard'
    _description = u"Wizard de sélection d'articles pour section sur modèle de devis"

    quote_id = fields.Many2one('sale.quote.template', string=u'Modèle de devis', required=True)
    quote_template_layout_category_id = fields.Many2one(
        'of.sale.quote.template.layout.category', string=u'Ligne de section')
    product_ids = fields.Many2many('product.product', string=u'Articles')

    def action_done(self):
        product_to_create = self.product_ids - self.quote_template_layout_category_id.product_ids
        product_to_delete = self.quote_template_layout_category_id.product_ids - self.product_ids

        res = []

        for line in self.quote_id.quote_line:
            if line.product_id in product_to_delete \
                    and line.of_layout_category_id == self.quote_template_layout_category_id:
                line.unlink()

        for product in product_to_create:
            quote_line = self.env['sale.quote.line'].create({
                'name': product.name_get()[0][1],
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'price_unit': product.lst_price,
                'quote_id': self.quote_template_layout_category_id.quote_id.id,
                'of_layout_category_id': self.quote_template_layout_category_id.id,
            })
            quote_line._onchange_product_id()

            res.append(quote_line)
        return res


class OfSelectOrderProductWizard(models.TransientModel):
    _name = 'of.select.order.product.wizard'
    _description = u"Wizard de sélection d'articles pour section sur devis/commande"

    order_id = fields.Many2one('sale.order', string=u'Commande', required=True)
    order_layout_category_id = fields.Many2one(
        'of.sale.order.layout.category', string=u'Ligne de section')
    product_ids = fields.Many2many('product.product', string=u'Articles')

    def action_done(self):
        product_to_create = self.product_ids - self.order_layout_category_id.product_ids
        product_to_delete = self.order_layout_category_id.product_ids - self.product_ids

        res = []

        for line in self.order_id.order_line:
            if line.product_id in product_to_delete and line.of_layout_category_id == self.order_layout_category_id:
                line.unlink()

        for product in product_to_create:
            order_line = self.env['sale.order.line'].create({
                'name': product.name,
                'product_id': product.id,
                'order_id': self.order_id.id,
                'of_layout_category_id': self.order_layout_category_id.id,
            })
            order_line.product_id_change()

            res.append(order_line)
        return res
