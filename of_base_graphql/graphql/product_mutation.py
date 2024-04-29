import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .product_category_type import ProductCategoryInput
from .product_type import Product


class ProductCreate(graphene.Mutation):
    _name = 'ProductCreate'

    class Arguments:
        name = graphene.String()
        list_price = graphene.Float()
        category = graphene.Argument(ProductCategoryInput)

    Output = Product

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['product.product']._prepare_mutation_values(**args)
        return env['product.product'].create(values)


class ProductUpdate(graphene.Mutation):
    _name = 'ProductUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        list_price = graphene.Float()
        category = graphene.Argument(ProductCategoryInput)

    Output = Product

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['product.product']._prepare_mutation_values(**args)
        product = env['product.product'].search([('id', '=', id)])
        product.write(values)
        return product


class ProductDelete(graphene.Mutation):
    _name = 'ProductDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = Product

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'product.product', id)


class ProductMutation(graphene.ObjectType):
    _name = 'ProductMutation'
    _type = 'mutation'

    product_create = ProductCreate.Field()
    product_update = ProductUpdate.Field()
    product_delete = ProductDelete.Field()
