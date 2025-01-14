# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_industry_graphql.graphql.technical_attribute_type import TechnicalAttribute


class OFEquipment(models.Model):
    _inherit = "of.equipment"

    @api.model
    def _prepare_technical_attributes(self):
        attributes = super()._prepare_technical_attributes()

        if self.industry_code == "refrigerant":
            attributes.extend(
                [
                    TechnicalAttribute(key="total_load", value=self.total_load),
                    TechnicalAttribute(
                        key="permanent_leak_detection_system",
                        value=self.permanent_leak_detection_system,
                    ),
                    TechnicalAttribute(key="fluid_nature", value=self.fluid_nature_id.id or None),
                ]
            )

        return attributes

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)
        if technical_attributes := args.get("technical_attributes"):
            for attribute in technical_attributes:
                value = attribute.value
                if attribute.key == "total_load":
                    mutation["total_load"] = value
                elif attribute.key == "permanent_leak_detection_system":
                    mutation["permanent_leak_detection_system"] = value
                elif attribute.key == "fluid_nature":
                    if isinstance(value, str):
                        value = int(value)
                    mutation["fluid_nature_id"] = value
        return mutation
