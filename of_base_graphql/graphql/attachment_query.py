import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .attachment_type import Attachment, AttachmentFilterInput


class AttachmentQuery(graphene.ObjectType):
    _name = 'AttachmentQuery'
    _type = 'query'

    attachments = graphene.List(
        graphene.NonNull(Attachment),
        filter=graphene.Argument(AttachmentFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_attachments(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {'id': 'int'}

        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.res_model:
                odoo_domain += [('res_model', '=', filter.res_model)]
            if filter.res_id:
                odoo_domain += [('res_id', '=', filter.res_id)]

        return env['ir.attachment'].search(odoo_domain, offset=offset, limit=limit)
