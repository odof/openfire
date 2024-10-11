# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = "of.planning.intervention.template"

    sheet_equipment = fields.Boolean(
        string="EQUIPMENT (IS)", help="Selects or deselects all equipment-related items to be displayed."
    )
    sheet_equipment_name = fields.Boolean(
        string="Serial Number (IS)", help='Adds the serial number in the "Equipment" section of the PDF document.'
    )
    sheet_equipment_product_id = fields.Boolean(
        string="Product (IS)", help='Adds the equipment name to the "Equipment" section of the PDF document.'
    )
    sheet_equipment_model = fields.Boolean(
        string="Model (IS)", help='Adds the equipment model to the "Equipment" section of the PDF document.'
    )
    sheet_equipment_brand_id = fields.Boolean(
        string="Brand (IS)", help='Adds the equipment mark to the "Equipment" section of the PDF document.'
    )
    sheet_equipment_product_category_id = fields.Boolean(
        string="Category (IS)", help='Adds the equipment category to the "Equipment" section of the PDF document.'
    )
    sheet_equipment_installation_date = fields.Boolean(
        string="Installation Date (IS)",
        help='Adds the equipment installation date to the "Equipment" section of the PDF document.',
    )
    sheet_equipment_installation_type = fields.Boolean(
        string="Installation Type (IS)",
        help='Adds equipment installation type to the "Equipment" section of the PDF document.',
    )
    sheet_equipment_is_compliant = fields.Boolean(
        string="Compliant (IS)", help='Adds equipment conformity to the "Equipment" section of the PDF document.'
    )
    sheet_equipment_installer_id = fields.Boolean(
        string="Installer (IS)", help='Adds the equipment installer to the "Equipment" section of the PDF document.'
    )
    sheet_equipment_note = fields.Boolean(
        string="Note (IS)", help='Adds the equipment information note to the "Equipment" section of the PDF document.'
    )

    report_equipment = fields.Boolean(
        string="EQUIPMENT (IR)", help="Select or deselect all equipment-related items to be displayed."
    )
    report_equipment_name = fields.Boolean(
        string="Serial Number (IR)", help='Adds the serial number in the "Equipment" section of the PDF document.'
    )
    report_equipment_product_id = fields.Boolean(
        string="Product (IR)", help='Adds the equipment name to the "Equipment" section of the PDF document.'
    )
    report_equipment_model = fields.Boolean(
        string="Model (IR)", help='Adds the equipment model to the "Equipment" section of the PDF document.'
    )
    report_equipment_brand_id = fields.Boolean(
        string="Brand (IR)", help='Adds the equipment mark to the "Equipment" section of the PDF document.'
    )
    report_equipment_product_category_id = fields.Boolean(
        string="Category (IR)", help='Adds the equipment category to the "Equipment" section of the PDF document.'
    )
    report_equipment_installation_date = fields.Boolean(
        string="Installation Date (IR)",
        help='Adds the equipment installation date to the "Equipment" section of the PDF document.',
    )
    report_equipment_installation_type = fields.Boolean(
        string="Installation Type (IR)",
        help='Adds equipment installation type to the "Equipment" section of the PDF document.',
    )
    report_equipment_is_compliant = fields.Boolean(
        string="Compliant (IR)", help='Adds equipment conformity to the "Equipment" section of the PDF document.'
    )
    report_equipment_installer_id = fields.Boolean(
        string="Installer (IR)", help='Adds the equipment installer to the "Equipment" section of the PDF document.'
    )
    report_equipment_note = fields.Boolean(
        string="Note (IR)", help='Adds the equipment information note to the "Equipment" section of the PDF document.'
    )

    @api.onchange("sheet_equipment")
    def _onchange_sheet_equipment(self):
        if self.sheet_equipment:
            event_keys = [key for key in self._fields.keys() if key.startswith("sheet_equipment_")]
            values = {key: True for key in event_keys}
            self.update(values)

    @api.onchange("report_equipment")
    def _onchange_report_equipment(self):
        if self.report_equipment:
            event_keys = [key for key in self._fields.keys() if key.startswith("report_equipment_")]
            values = {key: True for key in event_keys}
            self.update(values)
