# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .utm_source_type import UtmSource


class Partner(OdooObjectType):
    _name = "Partner"
    _type = "types"

    lead_source = graphene.Field(UtmSource)

    def resolve_lead_source(root, info):
        return root.of_lead_source_id or None
