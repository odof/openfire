# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_permanent_leak_detection_system = fields.Boolean(string="Permanent Leak Detection System")
    of_fluid_nature_id = fields.Many2one(comodel_name="of.fluid.nature", string="Fluid Nature")
    of_total_load = fields.Float(string="Total Load (kg)")
    of_co2_equivalent_tonnage = fields.Float(
        string="CO2 Equivalent Tonnage",
        compute="_compute_of_co2_equivalent_tonnage",
        store=True,
    )

    @api.depends("of_total_load", "of_fluid_nature_id")
    def _compute_of_co2_equivalent_tonnage(self):
        for product in self:
            if product.of_fluid_nature_id:
                product.of_co2_equivalent_tonnage = product.of_total_load * product.of_fluid_nature_id.gwp / 1000
            else:
                product.of_co2_equivalent_tonnage = 0

    def _compute_of_has_standard_attributes(self):
        super()._compute_of_has_standard_attributes()
        for record in self:
            if record.of_code == "refrigerant":
                record.of_has_standard_attributes = False

    def _compute_of_has_technical_attributes(self):
        super()._compute_of_has_technical_attributes()
        for record in self:
            if record.of_code == "refrigerant":
                record.of_has_technical_attributes = True
