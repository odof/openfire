import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .product_template_type import ProductTemplate, ProductTemplateCreateInput, ProductTemplateUpdateInput


class ProductTemplateCreate(graphene.Mutation):
    _name = 'ProductTemplateCreate'

    class Arguments:
        input = ProductTemplateCreateInput(required=True)

    Output = ProductTemplate

    def mutate(self, info, input):
        env = info.context["env"]

        return lazy_create(env, 'product.template', input)


class ProductTemplateUpdate(graphene.Mutation):
    _name = 'ProductTemplateUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ProductTemplateUpdateInput(required=True)

    Output = ProductTemplate

    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, 'product.template', id, input)


class ProductTemplateDelete(graphene.Mutation):
    _name = 'ProductTemplateDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ProductTemplate

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'product.template', id)


class ProductTemplateMutation(graphene.ObjectType):
    _name = 'ProductTemplateMutation'
    _type = 'mutation'

    product_template_create = ProductTemplateCreate.Field()
    product_template_update = ProductTemplateUpdate.Field()
    product_template_delete = ProductTemplateDelete.Field()
