# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrQWeb(models.AbstractModel):
    _inherit = 'ir.qweb'

    @api.model
    def _get_view_id(self, template):
        if isinstance(template, str) and '.' in template:
            left, right = template.rsplit('.', 1)
            if left == 'of_custom_document' and right.isdigit():
                template = 'of_custom_document.report_of_custom_document'
        return super()._get_view_id(template)
