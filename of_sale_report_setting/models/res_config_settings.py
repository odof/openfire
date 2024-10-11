# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def action_button_printings_params(self):
        return {
            "name": _("Configure PDF printing"),
            "type": "ir.actions.act_window",
            "res_model": "of.sale.document.layout",
            "view_mode": "form",
            "view_type": "form",
            "view_id": self.env.ref("of_sale_report_setting.of_sale_report_setting_sale_document_layout").id,
            "target": "new",
        }
