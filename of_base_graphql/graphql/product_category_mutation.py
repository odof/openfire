import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .product_category_type import ProductCategory, ProductCategoryCreateInput, ProductCategoryUpdateInput


class ProductCategoryCreate(graphene.Mutation):
    _name = 'ProductCategoryCreate'

    class Arguments:
        input = ProductCategoryCreateInput(required=True)

    Output = ProductCategory

    def mutate(self, info, input):
        env = info.context["env"]

        return lazy_create(env, 'product.category', input)


class ProductCategoryUpdate(graphene.Mutation):
    _name = 'ProductCategoryUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ProductCategoryUpdateInput(required=True)

    Output = ProductCategory

    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, 'product.category', id, input)


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
