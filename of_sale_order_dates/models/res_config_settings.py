# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Invoice settings
    pdf_technical_visit_info_move = fields.Boolean(
        string="(OF) Technical visit date",
        help="Displays the technical visit in top information block in Invoice PDF report ?",
        config_parameter="of.sale.report.setting.account.move.pdf_technical_visit_info",
    )
