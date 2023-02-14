# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from odoo import models, api
from odoo.osv import expression


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
                    and args[i + 1][1] in ('like', 'ilike') \
                    and args[i + 1][2] == args[i + 2][2]:
                operator = args[i + 1][1]
                mots = args[i + 1][2].split()
                args2 += ['&'] * (len(mots) - 1)
                for mot in mots:
                    args2 += ['|', ('default_code', operator, mot), ('name', operator, mot)]
                i += 3
            else:
                args2.append(args[i])
                i += 1
        return super().search(args2, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            product_ids = []
            if operator in positive_operators:
                product_ids = list(
                    self._search([('default_code', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid))
                if not product_ids:
                    product_ids = list(
                        self._search([('barcode', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid))
            if not product_ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Modification OpenFire :
                # Odoo déconseille de mettre ensemble les recherches sur name et default_code à cause de
                # soucis de performance.
                # Nous le faisons quand-mêmme pour la recherche partielle sur chacun des deux champs en meme temps
                # Si le temps de calcul devient trop grand, il faudra repenser cette recherche
                product_ids = list(
                    self._search(args + ['|', ['default_code', operator, name], ['name', operator, name]], limit=limit))
                # Fin modification OpenFire
            elif not product_ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = expression.OR([
                    ['&', ('default_code', operator, name), ('name', operator, name)],
                    ['&', ('default_code', '=', False), ('name', operator, name)],
                ])
                domain = expression.AND([args, domain])
                product_ids = list(self._search(domain, limit=limit, access_rights_uid=name_get_uid))
            if not product_ids and operator in positive_operators:
                ptrn = re.compile(r'(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    product_ids = list(self._search(
                        [('default_code', '=', res.group(2))] + args, limit=limit, access_rights_uid=name_get_uid))
            # still no results, partner in context: search on supplier info as last hope to find something
            if not product_ids and self._context.get('partner_id'):
                suppliers_ids = self.env['product.supplierinfo']._search([
                    ('partner_id', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)], access_rights_uid=name_get_uid)
                if suppliers_ids:
                    product_ids = self._search(
                        [('product_tmpl_id.seller_ids', 'in', suppliers_ids)], limit=limit,
                        access_rights_uid=name_get_uid)
        else:
            product_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return product_ids
