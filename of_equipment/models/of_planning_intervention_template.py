# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    sheet_equipment = fields.Boolean(string="EQUIPMENT")
    sheet_equipment_name = fields.Boolean(string="Serial Number")
    sheet_equipment_product_id = fields.Boolean(string="Product")
    sheet_equipment_model = fields.Boolean(string="Model")
    sheet_equipment_brand_id = fields.Boolean(string="Brand")
    sheet_equipment_product_category_id = fields.Boolean(string="Category")
    sheet_equipment_installation_date = fields.Boolean(string="Installation Date")
    sheet_equipment_installation_type = fields.Boolean(string="Installation Type")
    sheet_equipment_is_compliant = fields.Boolean(string="Compliant")
    sheet_equipment_installer_id = fields.Boolean(string="Installer")
    sheet_equipment_note = fields.Boolean(string="Note")

    report_equipment = fields.Boolean(string="EQUIPMENT")
    report_equipment_name = fields.Boolean(string="Serial Number")
    report_equipment_product_id = fields.Boolean(string="Product")
    report_equipment_model = fields.Boolean(string="Model")
    report_equipment_brand_id = fields.Boolean(string="Brand")
    report_equipment_product_category_id = fields.Boolean(string="Category")
    report_equipment_installation_date = fields.Boolean(string="Installation Date")
    report_equipment_installation_type = fields.Boolean(string="Installation Type")
    report_equipment_is_compliant = fields.Boolean(string="Compliant")
    report_equipment_installer_id = fields.Boolean(string="Installer")
    report_equipment_note = fields.Boolean(string="Note")

    @api.onchange('sheet_equipment')
    def _onchange_sheet_equipment(self):
        if self.sheet_equipment:
            event_keys = [key for key in self._fields.keys() if key.startswith("sheet_equipment_")]
            values = {key: True for key in event_keys}
            self.update(values)

    @api.onchange('report_equipment')
    def _onchange_report_equipment(self):
        if self.report_equipment:
            event_keys = [key for key in self._fields.keys() if key.startswith("report_equipment_")]
            values = {key: True for key in event_keys}
            self.update(values)
