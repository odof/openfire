# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MigrationMigration(models.Model):
    _name = 'migration.migration'
    _rec_name = 'database_id'

    start_version = fields.Integer()
    end_version = fields.Integer()
    current_version = fields.Integer()
    database_id = fields.Many2one(comodel_name='migration.database', string="Database")
    state = fields.Selection([('todo', 'To Do'), ('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')])
    server_id = fields.Many2one(comodel_name='migration.server', string="Server")
    planning_date = fields.Datetime()
    partner_id = fields.Many2one(comodel_name='res.partner', related='database_id.partner_id', string="Partner")
    uid = fields.Char()
    clean_all = fields.Boolean()
    ttype = fields.Selection([('demo', 'Demo'), ('prod', 'Production')], string="Type")
    log_info = fields.Text()
    log_warning = fields.Text()
    log_error = fields.Text()

    @api.model
    def cron_launch_migration(self):
        # on va chercher les migrations qui doivent être lancées et on envoie la demande au serveur
        migrations = self.search([('state', '=', 'todo'), ('planning_date', '>=', fields.Datetime.now())])
        migrations.action_start_migration()

    @api.model
    def cron_status_migration(self):
        migrations = self.search([('state', '=', 'running'), ('uid', '!=', False)])
        migrations.action_status_migration()

    def action_running(self):
        self.write({'state': 'running'})

    def action_done(self):
        self.write({'state': 'done'})
        self.action_get_logs()
        self.action_get_dump()

    def action_failed(self):
        self.write({'state': 'failed'})
        self.action_get_logs()
        self.action_get_dump()

    def action_start_migration(self):
        for record in self:
            record.server_id.action_start_migration(record)

    def action_status_migration(self):
        for record in self:
            record.server_id.action_statut_migration(record)

    def action_get_logs(self):
        for record in self:
            record.server_id.action_get_logs(record)

    def action_get_dump(self):
        for record in self:
            record.server_id.action_get_dump(record)
