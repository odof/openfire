# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFPlanningInterventionTemplateLine(models.Model):
    _inherit = "of.planning.intervention.template.line"

    def _prepare_request_service_line_vals(self, request):
        self.ensure_one()
        if not request:
            return {}
        return {
            "product_id": self.product_id.id,
            "price_unit": self.price_unit,
            "qty": self.qty,
            "name": self.name,
            "request_id": request.id,
        }
