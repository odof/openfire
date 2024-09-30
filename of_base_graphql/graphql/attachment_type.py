# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_graphql.graphql.odoo_type import OdooImage


class AttachmentType(graphene.Enum):
    url = "url"
    binary = "binary"


class Attachment(OdooObjectType):
    _name = "Attachment"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    type = graphene.Field(AttachmentType)
    res_model = graphene.String(name="model")
    res_id = graphene.Int(name="model_id")
    datas = OdooImage()


class AttachmentInput(graphene.InputObjectType):
    _name = "AttachmentInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    res_model = graphene.String()
    res_id = graphene.Int()
    datas = OdooImage()


class AttachmentFilterInput(AttachmentInput):
    _name = "AttachmentFilterInput"
