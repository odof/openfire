# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_com_sector_id = fields.Many2one(
        comodel_name='of.sector',
        string="Commercial sector",
        compute='_compute_of_com_sector_id',
        store=True,
        readonly=False,
    )
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
            # TODO: Move the first if part the correct compute method to of_planning module when it will be migrated
            # (check the parameter's key it may have changed since the migration of "of_planning" module)
            automatic_sectors = self.env['ir.config_parameter'].sudo().get_param('of.planning.automatic_sectors')
            automatic_sectors = automatic_sectors and automatic_sectors.lower() in ('true', '1')
            if partner.zip and automatic_sectors:
                partner.of_tech_sector_id = (
                    self.env['of.sector']
                    .get_sector_from_zip_code(partner.zip)
                    .filtered(lambda sec: sec.type in ('technical', 'technical_commercial'))
                )
            elif partner.of_com_sector_id and partner.of_com_sector_id.type == 'technical_commercial':
                partner.of_tech_sector_id = partner.of_com_sector_id.id

    # TODO: Move me to of_planning module when it will be migrated
    # (check the parameter's key it may have changed since the migration of "of_planning" module)
    @api.depends('zip')
    def _compute_of_com_sector_id(self):
        for partner in self:
            automatic_sectors = self.env['ir.config_parameter'].sudo().get_param('of.planning.automatic_sectors')
            automatic_sectors = automatic_sectors and automatic_sectors.lower() in ('true', '1')
            if partner.zip and automatic_sectors:
                partner.of_com_sector_id = (
                    self.env['of.sector']
                    .get_sector_from_zip_code(partner.zip)
                    .filtered(lambda sec: sec.type in ('commercial', 'technical_commercial'))
                )
