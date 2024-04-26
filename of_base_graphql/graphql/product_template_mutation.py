import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .product_template_type import ProductTemplate


class ProductTemplateCreate(graphene.Mutation):
    _name = 'ProductTemplateCreate'

    class Arguments:
        name = graphene.String()
        list_price = graphene.Float()

    Output = ProductTemplate

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['product.template']._prepare_mutation_values(**args)
        return env['product.template'].create(values)


class ProductTemplateUpdate(graphene.Mutation):
    _name = 'ProductTemplateUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        list_price = graphene.Float()

    Output = ProductTemplate

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['product.template']._prepare_mutation_values(**args)
        product = env['product.template'].search([('id', '=', id)])
        return product.write(values)


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
