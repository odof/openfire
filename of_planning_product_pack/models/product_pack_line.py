# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import models


class OFProductPackLines(models.Model):
    _inherit = "product.pack.line"

    def _prepare_procurement_values_from_line(self, line, group_id=False):
        """Prepare the values for the procurement."""
        self.ensure_one()
        date_deadline = line.intervention_id.start
        date_planned = date_deadline - timedelta(days=line.intervention_id.of_company_id.security_lead)
        return {
            "group_id": group_id,
            "of_intervention_line_id": line.id,
            "date_planned": date_planned,
            "date_deadline": date_deadline,
            "warehouse_id": line.intervention_id.of_warehouse_id or False,
            "partner_id": line.intervention_id.of_address_id.id,
            "product_description_variants": line.name,
            "company_id": line.intervention_id.of_company_id,
            "sequence": line.sequence,
        }
