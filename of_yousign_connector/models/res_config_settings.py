# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_yousign_environment = fields.Selection(
        selection=[
            ("sandbox", "Sandbox"),
            ("production", "Production"),
        ],
        string="Environment",
        config_parameter="of.yousign.connector.yousign_environment",
        help="Choose the environment used for the YouSign requests",
    )
    of_yousign_sms_otp_content = fields.Char(
        string="SMS authentification message",
        size=105,
        config_parameter="of.yousign.connector.yousign_sms_otp_content",
        help="This message will be used for signers using the SMS authentication mode",
    )
