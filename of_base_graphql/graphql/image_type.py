# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_graphql.graphql.odoo_type import OdooImage


class Image(OdooObjectType):
    _name = 'Image'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(default_value="")
    caption = graphene.String(default_value="")
    sequence = graphene.Int(default_value=1)
    printable = graphene.Boolean(default_value=True)
    image_1920 = OdooImage()


class ImageInput(graphene.InputObjectType):
    _name = 'ImageInput'
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    caption = graphene.String()
    sequence = graphene.Int()
    printable = graphene.Boolean()
    image_1920 = OdooImage()


class ImageFilterInput(ImageInput):
    _name = 'ImageFilterInput'
