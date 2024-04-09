import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .product_category_mutation import ProductCategoryCreate, ProductCategoryUpdate
from .product_category_type import ProductCategoryInput
from .product_type import Product, ProductCreateInput, ProductUpdateInput


class ProductCreate(graphene.Mutation):
    _name = 'ProductCreate'

    class Arguments:
        input = ProductCreateInput(required=True)
        category = ProductCategoryInput()

    Output = Product

    def mutate(self, info, input, category=None):
        env = info.context["env"]

        if category:
            if category.id:
                category = ProductCategoryUpdate().mutate(info, id=category.id, input=category)
            else:
                category = ProductCategoryCreate().mutate(info, input=category)

        product = lazy_create(env, 'product.product', input)

        if category:
            product.categ_id = category

        return product


class ProductUpdate(graphene.Mutation):
    _name = 'ProductUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ProductUpdateInput(required=True)
        category = ProductCategoryInput()

    Output = Product

    def mutate(self, info, id, input, category=None):
        env = info.context["env"]

        if category:
            if category.id:
                category = ProductCategoryUpdate().mutate(info, id=category.id, input=category)
            else:
                category = ProductCategoryCreate().mutate(info, input=category)

        product = lazy_update(env, 'product.product', id, input)

        if category:
            product.categ_id = category

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
