# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class WizardCreateMigration(models.TransientModel):
    _name = 'create.migration.wizard'

    start_version = fields.Integer()
    end_version = fields.Integer()
    database_id = fields.Many2one(comodel_name='migration.database', string="Database")
    server_id = fields.Many2one(comodel_name='migration.server', string="Server", domain=[('ttype', '=', 'migration')])
    planning_date = fields.Datetime()
    clean_all = fields.Boolean()
    ttype = fields.Selection([('demo', 'Demo'), ('prod', 'Production')], string="Type", default='demo')

    def action_create_migration(self):
        if self.end_version <= self.start_version:
            raise UserError(_("End version must be bigger than start version"))

        if not self.server_id:
            server = self.env['migration.server'].search([], limit=1)
        else:
            server = self.server_id

        if not self.planning_date:
            planning_date = fields.Datetime.now()
        else:
            planning_date = self.planning_date

        value = {
            'start_version': self.start_version,
            'end_version': self.end_version,
            'database_id': self.database_id.id,
            'server_id': server.id,
            'planning_date': planning_date,
            'clean_all': self.clean_all,
            'ttype': self.ttype,
            'state': 'todo',
        }

        migration = self.env['migration.migration'].create(value)
        return {
            'name': 'Migration',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'migration.migration',
            'res_id': migration.id,
            'target': 'self',
        }
