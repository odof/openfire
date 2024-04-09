# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .product_category_type import ProductCategory


class ProductCategoryCreate(graphene.Mutation):
    _name = 'ProductCategoryCreate'

    class Arguments:
        name = graphene.String()

    Output = ProductCategory

    def mutate(self, info, **args):
        env = info.context['env']
        values = env['product.category']._prepare_mutation_values(**args)
        return env['product.category'].create(values)


class ProductCategoryUpdate(graphene.Mutation):
    _name = 'ProductCategoryUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()

    Output = ProductCategory

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['product.category']._prepare_mutation_values(**args)
        category = env['product.category'].search([('id', '=', id)])
        category.write(values)
        return category


class ProductCategoryDelete(graphene.Mutation):
    _name = 'ProductCategoryDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ProductCategory

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'product.category', id)


class ProductCategoryMutation(graphene.ObjectType):
    _name = 'ProductCategoryMutation'
    _type = 'mutation'

    product_category_create = ProductCategoryCreate.Field()
    product_category_update = ProductCategoryUpdate.Field()
    product_category_delete = ProductCategoryDelete.Field()
