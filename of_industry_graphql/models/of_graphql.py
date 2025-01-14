# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.technical_attribute_schema_query import TechnicalAttributeSchemaQuery
from ..graphql.technical_attribute_schema_type import TechnicalAttributeSchema
from ..graphql.technical_attribute_type import TechnicalAttribute, TechnicalAttributeInput


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_industry_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                TechnicalAttribute,
                TechnicalAttributeSchema,
                TechnicalAttributeSchemaQuery,
                TechnicalAttributeInput,
            ],
        )
