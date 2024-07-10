# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class Company(OdooObjectType):
    _name = 'Company'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
