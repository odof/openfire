# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    """
    Customise the company document layout and display a live preview
    """

    _inherit = "base.document.layout"

    of_logo_ids = fields.Many2many(related="company_id.of_logo_ids")
    of_use_logo_footer = fields.Boolean(related="company_id.of_use_logo_footer")

    def _get_footer_logos(self):
        self.ensure_one()
        return self.of_logo_ids.filtered(lambda s: s.logo_position == "footer")

    def _get_footer_corner_logos(self):
        self.ensure_one()
        return self.of_logo_ids.filtered(lambda s: s.logo_position in ("footer_right_corner", "footer_left_corner"))

    def _get_footer_right_corner_logos(self):
        self.ensure_one()
        return self._get_footer_corner_logos().filtered(lambda s: s.logo_position == "footer_right_corner")

    def _get_footer_left_corner_logos(self):
        self.ensure_one()
        return self._get_footer_corner_logos().filtered(lambda s: s.logo_position == "footer_left_corner")
