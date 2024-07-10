# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .image_type import Image, ImageFilterInput


class ImageQuery(graphene.ObjectType):
    _name = 'ImageQuery'
    _type = 'query'

    images = graphene.List(
        graphene.NonNull(Image),
        select=graphene.Argument(ImageFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_images(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.image']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.image'].search(odoo_domain, offset=offset, limit=limit)
