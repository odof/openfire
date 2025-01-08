# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFEquipment(models.Model):
    _inherit = "of.equipment"

    industry_id = fields.Many2one(comodel_name="of.industry", string="Industry")
    industry_code = fields.Char(related="industry_id.code")

    has_technical_attributes = fields.Boolean(
        string="Has technical attributes",
        compute="_compute_has_technical_attributes",
    )

    @api.depends("industry_code")
    def _compute_has_technical_attributes(self):
        print("super")
        for record in self:
            record.has_technical_attributes = False
