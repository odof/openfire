# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class OFProductSearchCategory(models.Model):
    _name = 'of.product.search.category'
    _description = u"Catégorie de recherche"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'

    name = fields.Char(string=u"Name", index=True, required=True, translate=True)
    parent_id = fields.Many2one(
        comodel_name='of.product.search.category', string=u"Parent Category", index=True, ondelete='cascade')
    child_id = fields.One2many(
        comodel_name='of.product.search.category', inverse_name='parent_id', string=u"Child Categories")
    type = fields.Selection(
        selection=[('view', u"View"), ('normal', u"Normal")], string=u"Category Type", default='normal',
        help=u"A category of the view type is a virtual category that can be used as the parent "
             u"of another category to create a hierarchical structure.")
    parent_left = fields.Integer(string=u"Left Parent", index=1)
    parent_right = fields.Integer(string=u"Right Parent", index=1)
    product_count = fields.Integer(
        string=u"# Products", compute='_compute_product_count',
        help=u"The number of products under this category (Does not consider the children categories)")

    def _compute_product_count(self):
        read_group_res = self.env['product.template'].read_group(
            [('of_product_search_category_id', 'child_of', self.ids)],
            ['of_product_search_category_id'],
            ['of_product_search_category_id'])
        group_data = dict(
            (data['of_product_search_category_id'][0], data['of_product_search_category_id_count'])
            for data in read_group_res)
        for categ in self:
            product_count = 0
            for sub_categ_id in categ.search([('id', 'child_of', categ.id)]).ids:
                product_count += group_data.get(sub_categ_id, 0)
            categ.product_count = product_count

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_(u"Error ! You cannot create recursive categories."))
        return True

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res

        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symmetric to name_get
            category_names = name.split(' / ')
            parents = list(category_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args, operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('parent_id', 'in', categories.ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', category_ids)], domain])
                for i in range(1, len(category_names)):
                    domain = [[('name', operator, ' / '.join(category_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]), limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_product_search_category_id = fields.Many2one(
        comodel_name='of.product.search.category', string=u"Catégorie de recherche")