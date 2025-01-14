# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_industry_graphql.graphql.technical_attribute_schema_type import (
    TechnicalAttributeSchema,
    TechnicalAttributeType,
)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _prepare_technical_attribute_schemas(self):
        attributes = super()._prepare_technical_attribute_schemas()
        attributes.extend(
            [
                TechnicalAttributeSchema(
                    name="Charge totale (kg)",
                    key="total_load",
                    ttype=TechnicalAttributeType.FLOAT,
                    required=False,
                    readonly=False,
                ),
                TechnicalAttributeSchema(
                    name="Système permanent de détection de fuite",
                    key="permanent_leak_detection_system",
                    ttype=TechnicalAttributeType.BOOLEAN,
                    required=False,
                    readonly=False,
                ),
                TechnicalAttributeSchema(
                    name="Nature du fluide",
                    key="fluid_nature",
                    ttype=TechnicalAttributeType.MANY2ONE_ID,
                    required=False,
                    readonly=False,
                ),
            ]
        )
        return attributes
