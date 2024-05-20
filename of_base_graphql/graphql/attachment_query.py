import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .attachment_type import Attachment, AttachmentFilterInput


class AttachmentQuery(graphene.ObjectType):
    _name = 'AttachmentQuery'
    _type = 'query'

    attachments = graphene.List(
        graphene.NonNull(Attachment),
        select=graphene.Argument(AttachmentFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_attachments(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]

        odoo_domain = env['ir.attachment']._prepare_graphql_domain(select=select, domain=domain)

        return env['ir.attachment'].search(odoo_domain, offset=offset, limit=limit)
