# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[("activities_lot", "Activities lot")])
    of_activities_type = fields.Many2many(
        comodel_name="mail.activity.type",
        relation="mail_activity_type_mail_activity_type_rel",
        column1="parent_id",
        column2="child_id",
        string="Activities",
    )
