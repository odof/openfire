# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class UtmSource(OdooObjectType):
    _name = 'UtmSource'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
