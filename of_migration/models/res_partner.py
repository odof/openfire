# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    database_ids = fields.One2many(comodel_name='migration.database', inverse_name='partner_id', string="Databases")
    migration_ids = fields.One2many(comodel_name='migration.migration', inverse_name='partner_id', string="Migrations")
    script_ids = fields.Many2many(comodel_name='migration.sql', string="Scripts")
