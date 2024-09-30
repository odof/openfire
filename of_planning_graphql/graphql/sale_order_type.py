# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class SaleOrder(OdooObjectType):
    _name = "SaleOrder"
    _type = "types"

    of_intervention_notes = graphene.String(name="interventionNotes")
