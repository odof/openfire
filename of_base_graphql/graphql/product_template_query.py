import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .product_template_type import ProductTemplate, ProductTemplateFilterInput


class ProductTemplateQuery(graphene.ObjectType):
    _name = 'ProductTemplateQuery'
    _type = 'query'

    product_templates = graphene.List(
        graphene.NonNull(ProductTemplate),
        filter=graphene.Argument(ProductTemplateFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_product_templates(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = []
        odoo_type = {'id': 'int', 'categ_id': 'int', 'list_price': 'float', 'company_id': 'int', 'of_mobile': 'boolean'}
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.ref:
                odoo_domain += [('ref', 'ilike', filter.ref)]

        return env['product.template'].search(odoo_domain, offset=offset, limit=limit)
