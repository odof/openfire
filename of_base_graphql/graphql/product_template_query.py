import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .product_template_type import ProductTemplate, ProductTemplateFilterInput


class ProductTemplateQuery(graphene.ObjectType):
    _name = 'ProductTemplateQuery'
    _type = 'query'

    product_templates = graphene.List(
        graphene.NonNull(ProductTemplate),
        select=graphene.Argument(ProductTemplateFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_product_templates(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['product.template']._prepare_graphql_domain(select=select, domain=domain)
        return env['product.template'].search(odoo_domain, offset=offset, limit=limit)
