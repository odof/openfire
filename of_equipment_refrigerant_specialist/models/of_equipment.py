# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFEquipment(models.Model):
    _inherit = "of.equipment"

    permanent_leak_detection_system = fields.Boolean(string="Permanent Leak Detection System", tracking=True)
    fluid_nature_id = fields.Many2one(comodel_name="of.fluid.nature", string="Fluid Nature", tracking=True)
    total_load = fields.Float(string="Total Load (kg)", tracking=True)
    co2_equivalent_tonnage = fields.Float(
        string="CO2 Equivalent Tonnage",
        compute="_compute_co2_equivalent_tonnage",
        store=True,
    )

    @api.depends("total_load", "fluid_nature_id")
    def _compute_co2_equivalent_tonnage(self):
        for record in self:
            if record.fluid_nature_id:
                record.co2_equivalent_tonnage = record.total_load * record.fluid_nature_id.gwp / 1000
            else:
                record.co2_equivalent_tonnage = 0

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.industry_id = self.product_id.of_industry_id
            self.permanent_leak_detection_system = self.product_id.of_permanent_leak_detection_system
            self.fluid_nature_id = self.product_id.of_fluid_nature_id
            self.total_load = self.product_id.of_total_load

    def _compute_has_technical_attributes(self):
        super()._compute_has_technical_attributes()
        for record in self:
            if record.industry_code == "refrigerant":
                record.has_technical_attributes = True
