# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class UtmMixin(models.AbstractModel):
    _inherit = 'utm.mixin'

    medium_id = fields.Many2one(string="Channel")
    source_id = fields.Many2one(
        string="Origin", domain="[('medium_id', '=', medium_id)]",
        compute='_compute_source_id', store=True, readonly=False)

    @api.onchange('medium_id')
    def _compute_source_id(self):
        for record in self:
            if record.medium_id:
                record.source_id = record.medium_id.source_ids and record.medium_id.source_ids[0] or False
            else:
                record.source_id = False
