# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    of_article_principal = fields.Boolean(string="Article principal",
                                          help=u"Les articles de cette catégorie seront considérés comme articles"
                                               u" principaux sur les commandes / factures clients")
    of_taux_marge = fields.Integer(
        string="Taux de marge",
        help=u"Taux de marge en % minimum recommandé quand l'article principal d'un devis fait partie"
             u" de la catégorie.")

    @api.constrains('of_taux_marge')
    def _constraint_taux_marge(self):
        for category in self:
            if category.of_taux_marge < 0 or category.of_taux_marge > 100:
                raise UserError("Le taux de marge doit être compris entre 0% et 100%")


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.multi
    def of_is_quantity_dependent(self, product_id, date_eval=fields.Date.today()):
        u"""
            :param: product_id Produit évalué
            :param: date_eval Date d'évaluation de la liste de prix
            :return: True si le produit évalué est contenu dans cette liste et que son prix dépend de la quantité
        """
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        for item in self.item_ids:
            if item.min_quantity and item.min_quantity > 1:
                # une date de début pour cet item et la date d'évaluation antérieure à cette date de début
                if item.date_start and date_eval < item.date_start:
                    continue
                # une date de fin pour cet item et la date d'évaluation postérieure à cette date de fin
                if item.date_end and date_eval > item.date_end:
                    continue
                # l'item s'applique sur une catégorie d'article différente de celle de l'article évalué
                if item.applied_on == '2_product_category' and item.categ_id \
                        and item.categ_id != product.product_tmpl_id.categ_id:
                    continue
                # l'item s'applique sur un article différent de l'article évalué
                if item.applied_on == '1_product' and item.product_tmpl_id \
                        and item.product_tmpl_id != product.product_tmpl_id:
                    continue
                # l'item s'applique sur une variante différente de la variante évaluée
                if item.applied_on == '0_product_variant' and item.product_id and item.product_id != product:
                    continue
                return True
        return False


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_product_image_ids = fields.One2many('of.product.image', 'product_tmpl_id', string=u'Images')

    @api.multi
    def action_view_sales(self):
        self.ensure_one()
        action = self.env.ref('sale.action_product_sale_list')
        product_ids = self.with_context(active_test=False).product_variant_ids.ids

        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': "{'default_product_id': " + str(product_ids[0]) + "}",
            'res_model': action.res_model,
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _sales_count(self):
        r = {}
        domain = [
            ('product_id', 'in', self.ids),
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            product.sales_count = r.get(product.id, 0)
        return r

    @api.multi
    def write(self, values):
        res = super(ProductProduct, self).write(values)
        # Si une variante est archivée, on regarde si d'autres variantes sont encore active,
        # sinon, on archive aussi le modèle d'article
        # no rebound dans le context pour éviter une boucle infinie : archiver un template archive ses variantes
        if 'active' in values and not values['active'] and res and not self._context.get('of_no_rebound'):
            to_deactivate = self.env['product.template']
            for product in self:
                variants = self.search_count([('product_tmpl_id', '=', product.product_tmpl_id.id)])
                if not variants:
                    to_deactivate |= product.product_tmpl_id
            to_deactivate.with_context(of_no_rebound=True).write({'active': False})
        # Si une variante est désarchivée, on regarde si son template est actif
        # sinon, on active aussi le modèle d'article
        # no rebound dans le context pour éviter une boucle infinie : activer un template active ses variantes
        if 'active' in values and values['active'] and res and not self._context.get('of_no_rebound'):
            to_activate = self.env['product.template']
            for product in self:
                if not product.product_tmpl_id.active:
                    to_activate |= product.product_tmpl_id
            to_activate.with_context(of_no_rebound=True).write({'active': True})
        return res


class OfProductImage(models.Model):
    _name = 'of.product.image'
    _description = 'Product Images'

    name = fields.Char('Name')
    image = fields.Binary('Image', attachment=True)
    product_tmpl_id = fields.Many2one('product.template', 'Related Product', copy=True)
