# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CRMStage(models.Model):
    _inherit = "crm.stage"

    of_auto_model_name = fields.Selection(
        selection=[], string="Model"  # Empty selection to be filled by inherited modules
    )
    of_auto_field_id = fields.Many2one(comodel_name="ir.model.fields", string="Field")
    of_auto_comparison_code = fields.Char(string="Comparison code")
    of_manual_activity_id = fields.Many2one(
        comodel_name="mail.activity.type", string="Activity to be created in case of manual update"
    )
