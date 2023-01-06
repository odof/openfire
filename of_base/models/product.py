# -*- coding: utf-8 -*-

import re

from odoo import models, api
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Recherche multi-mots
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args2 = []
        i = 0
        while i < len(args):
            if args[i] == '|' \
                    and isinstance(args[i + 1], (list)) and args[i + 1][0] == 'default_code' \
                    and isinstance(args[i + 2], (list)) and args[i + 2][0] == 'name' \
                    and args[i+1][1] in ('like', 'ilike') \
                    and args[i + 1][2] == args[i + 2][2]:
                operator = args[i+1][1]
                mots = args[i+1][2].split()
                args2 += ['&'] * (len(mots) - 1)
                for mot in mots:
                    args2 += ['|', ('default_code', operator, mot), ('name', operator, mot)]
                i += 3
            else:
                args2.append(args[i])
                i += 1
        return super(ProductTemplate, self).search(args2, offset=offset, limit=limit, order=order, count=count)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Recherche multi-mots
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args2 = []
        i = 0
        while i < len(args):
            if args[i] == '|' \
                    and isinstance(args[i + 1], (list)) and args[i + 1][0] == 'default_code' \
                    and isinstance(args[i + 2], (list)) and args[i + 2][0] == 'name' \
                    and args[i+1][1] in ('like', 'ilike') \
                    and args[i + 1][2] == args[i + 2][2]:
                operator = args[i+1][1]
                mots = args[i+1][2].split()
                args2 += ['&'] * (len(mots) - 1)
                for mot in mots:
                    args2 += ['|', ('default_code', operator, mot), ('name', operator, mot)]
                i += 3
            else:
                args2.append(args[i])
                i += 1
        return super(ProductProduct, self).search(args2, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            products = self.env['product.product']
            if operator in positive_operators:
                products = self.search([('default_code', '=', name)] + args, limit=limit)
                if not products:
                    products = self.search([('barcode', '=', name)] + args, limit=limit)
            if not products and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Modification OpenFire :
                # Odoo déconseille de mettre ensemble les recherches sur name et default_code à cause de soucis de performance
                # Nous le faisons quand-mêmme pour la recherche partielle sur chacun des deux champs en meme temps
                # Si le temps de calcul devient trop grand, il faudra repenser cette recherche
                products = self.search(args + ['|', ['default_code', operator, name], ['name', operator, name]], limit=limit)
            elif not products and operator in expression.NEGATIVE_TERM_OPERATORS:
                products = self.search(args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit)
            if not products and operator in positive_operators:
                ptrn = re.compile(r'(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    products = self.search([('default_code', '=', res.group(2))] + args, limit=limit)
            # still no results, partner in context: search on supplier info as last hope to find something
            if not products and self._context.get('partner_id'):
                suppliers = self.env['product.supplierinfo'].search([
                    ('name', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)])
                if suppliers:
                    products = self.search([('product_tmpl_id.seller_ids', 'in', suppliers.ids)], limit=limit)
        else:
            products = self.search(args, limit=limit)
        return products.name_get()
