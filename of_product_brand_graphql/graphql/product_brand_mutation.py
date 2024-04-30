import graphene

from odoo.addons.of_base_graphql.graphql.product_template_type import ProductTemplateInput
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .product_brand_type import ProductBrand


class ProductBrandCreate(graphene.Mutation):
    _name = 'ProductBrandCreate'

    class Arguments:
        name = graphene.String()
        active = graphene.Boolean()
        code = graphene.String()
        use_prefix = graphene.Boolean()
        supplier_delay = graphene.Int()
        product_templates = graphene.List(graphene.NonNull(ProductTemplateInput))
        products = graphene.List(graphene.NonNull(ProductInput))

    Output = ProductBrand

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.product.brand']._prepare_mutation_values(**args)
        return env['of.product.brand'].create(values)


class ProductBrandUpdate(graphene.Mutation):
    _name = 'ProductBrandUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        active = graphene.Boolean()
        code = graphene.String()
        use_prefix = graphene.Boolean()
        supplier_delay = graphene.Int()
        product_templates = graphene.List(graphene.NonNull(ProductTemplateInput))
        products = graphene.List(graphene.NonNull(ProductInput))

    Output = ProductBrand

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.product.brand']._prepare_mutation_values(**args)
        brand = env['of.product.brand'].search([('id', '=', id)])
        brand.write(values)
        return brand


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
