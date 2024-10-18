# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def action_button_invoice_printings_params(self):
        return {
            "name": _("Configure PDF printing"),
            "type": "ir.actions.act_window",
            "res_model": "of.invoice.document.layout",
            "view_mode": "form",
            "view_type": "form",
            "view_id": self.env.ref("of_invoice_report_setting.of_invoice_document_layout_view_form").id,
            "target": "new",
            "context": self.env.context.copy(),
        }
