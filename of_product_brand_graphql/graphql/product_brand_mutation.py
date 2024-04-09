import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .product_brand_type import ProductBrand, ProductBrandCreateInput, ProductBrandUpdateInput


class ProductBrandCreate(graphene.Mutation):
    _name = 'ProductBrandCreate'

    class Arguments:
        input = ProductBrandCreateInput(required=True)

    Output = ProductBrand

    def mutate(self, info, input):
        env = info.context["env"]

        return lazy_create(env, 'of.product.brand', input)


class ProductBrandUpdate(graphene.Mutation):
    _name = 'ProductBrandUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ProductBrandUpdateInput(required=True)

    Output = ProductBrand

    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, 'of.product.brand', id, input)


class ProductBrandDelete(graphene.Mutation):
    _name = 'ProductBrandDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ProductBrand

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.product.brand', id)


class ProductBrandMutation(graphene.ObjectType):
    _name = 'ProductBrandMutation'
    _type = 'mutation'

    product_brand_create = ProductBrandCreate.Field()
    product_brand_update = ProductBrandUpdate.Field()
    product_brand_delete = ProductBrandDelete.Field()
