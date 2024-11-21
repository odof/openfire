# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningAvailableSlot(models.Model):
    _inherit = "of.planning.available.slot"

    type = fields.Selection(selection=[("regular", "Regular"), ("web", "Web")], required=True, default="regular")
