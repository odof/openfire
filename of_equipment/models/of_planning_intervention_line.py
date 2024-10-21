# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionLine(models.Model):
    _inherit = "of.planning.intervention.line"

    equipment_link_line_id = fields.Many2one(
        comodel_name="of.calendar.event.equipment.link.line", string="Invoicing equipment line"
    )
    equipment_link_id = fields.Many2one(related="equipment_link_line_id.link_id", string="Equipment link")
    equipment_id = fields.Many2one(related="equipment_link_id.equipment_id", string="Equipment")

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("of_equipment_line_no_sync") and any(
            field in vals for field in self.env["of.calendar.event.equipment.link.line"]._get_field_names_to_sync()
        ):
            self._sync_equipment_link_line([(line, vals) for line in self if line.equipment_link_line_id])
        return result

    def unlink(self):
        equipment_link_lines = self.mapped("equipment_link_line_id")
        result = super().unlink()
        equipment_link_lines.unlink()
        return result

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _sync_equipment_link_line(self, data=None):
        """Synchronize the intervention lines with the equipment link lines.

        Args:
            lines (list): A list of tuples containing the equipment link lines and the values to write on them.
        """
        if not data:
            return
        for line, vals in data:
            if values := self._build_equipment_link_line_values(line, vals):
                # Avoid infinite loop and posting event messages by adding a context key
                equipment_link_line_id = line.equipment_link_line_id.with_context(of_equipment_line_no_sync=True)
                equipment_link_line_id.write(values)
                equipment_link_line_id._compute_amount()
                equipment_link_line_id._compute_tax_ids()

    def _build_equipment_link_line_values(self, line, vals):
        """
        Build the values to update the equipment intervention line from the intervention line values.

        Args:
            line (of.planning.intervention.line): The intervention line to get the values from.

        Returns:
            dict: Values to update the intervention line.
        """
        return {field: vals[field] for field in line.equipment_link_line_id._get_field_names_to_sync() if field in vals}
