# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_com_sector_id = fields.Many2one(comodel_name='of.sector', string="Commercial sector")
    of_tech_sector_id = fields.Many2one(
        comodel_name='of.sector',
        string="Technical sector",
        compute='_compute_of_tech_sector_id',
        store=True,
        readonly=False,
    )

    @api.depends('of_com_sector_id', 'zip')
    def _compute_of_tech_sector_id(self):
        for partner in self:
            if partner.of_com_sector_id and partner.of_com_sector_id.type == 'technical_commercial':
                partner.of_tech_sector_id = partner.of_com_sector_id.id
