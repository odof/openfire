# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSectorZipRange(models.Model):
    _name = 'of.sector.zip.range'
    _order = 'zip_code_min, zip_code_max'

    name = fields.Char(string="Name displayed", compute='_compute_name', store=True)
    zip_code_min = fields.Char(string="Zip code start", required=True)
    zip_code_max = fields.Char(
        string="Zip code end", required=True, compute='_compute_zip_code_max', readonly=False, store=True
    )
    sector_id = fields.Many2one(comodel_name='of.sector', string="Sector", required=True, ondelete='cascade')

    @api.depends('zip_code_min', 'zip_code_max')
    def _compute_name(self):
        for zip_range in self:
            if zip_range.zip_code_min == zip_range.zip_code_max:
                zip_range.name = zip_range.zip_code_min
            else:
                zip_range.name = f'{zip_range.zip_code_min} - {zip_range.zip_code_max}'

    @api.depends('zip_code_min')
    def _compute_zip_code_max(self):
        self.ensure_one()
        self.zip_code_max = self.zip_code_min
