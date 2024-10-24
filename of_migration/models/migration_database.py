# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MigrationDatabase(models.Model):
    _name = 'migration.database'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    version = fields.Integer()
    status = fields.Selection([('ok', 'OK'), ('ko', 'KO')], default='ok')
    date_database = fields.Date(default=fields.Date.today)
    backup_type = fields.Selection([('file', 'File'), ('distant', 'Distant'), ('uuid', 'UUID')])
    backup_file = fields.Binary(attachment=True)
    backup_server = fields.Many2one(comodel_name='migration.server', domain=[('ttype', '=', 'backup')])
    backup_filename = fields.Char()
    backup_uuid = fields.Char()
    script_ids = fields.Many2many(comodel_name='migration.sql', string="Scripts")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('scripts_ids'):
                vals['script_ids'] = self.env['res.partner'].browse(vals['partner_id']).script_ids
        return super().create(vals_list)

    def button_action_create_migration(self):
        wz_value = {
            'database_id': self.id,
            'start_version': self.version,
            'end_version': self.version + 1,
        }
        wz = self.env['create.migration.wizard'].create(wz_value)

        return {
            'name': 'Migration',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'create.migration.wizard',
            'res_id': wz.id,
            'target': 'new',
        }
