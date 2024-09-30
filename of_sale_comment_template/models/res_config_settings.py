# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_propagate_comments_settings = fields.Selection(
        selection=[
            ("do_not_keep_comments", "Do not keep comments"),
            ("keep_comments", "Keep comments"),
            ("keep_top_comment", "Keep the top comment"),
            ("keep_bottom_comment", "Keep the bottom comment"),
        ],
        config_parameter="of.sale.comment.template.propagate_comments",
        string="(OF) Comments propagation",
        help="Select the way comments are propagated from the sale order to the invoice.",
    )
