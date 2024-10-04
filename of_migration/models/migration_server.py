# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
from slugify import slugify

from odoo import api, fields, models


class MigrationServer(models.Model):
    _name = 'migration.server'

    name = fields.Char()
    host = fields.Char()
    state = fields.Char()
    authentication_id = fields.Many2one(comodel_name='migration.authentication', string="Authentication")

    def connect(self):
        return True

    def action_start_migration(self, migration):
        if self.connect():
            # on envoie le fichier sur le serveur distant
            res = requests.post(f"{self.host}/api/uploads", data=migration.backup_file)
            res_file = res.json()

            # on envoie les scripts s'ils n'y sont pas déjà
            for script in migration.script_ids:
                value_script = {
                    'id': script.id,
                    'name': script.name,
                    'version': script.version,
                    'sous_version': script.subversion,
                    'post_script': script.post_script,
                    'pre_script': script.pre_script,
                }
                res = requests.post(f"{self.host}/api/sql", data=value_script)

            value_migration = {
                'client': f"{slugify(migration.partner_id.name)}-{migration.partner_id.id}",
                'debut': migration.start,
                'fin': migration.end,
                'clean_all': migration.clean_all,
                'type': migration.type,
                'file_uid': res_file.get('uid'),
                'scripts': migration.script_ids.ids,
            }

            res = requests.post(f"{self.host}/api/migration", data=value_migration)
            migration.uid = res.get('uid')
            migration.action_running()

    def action_status_migration(self, migration):
        if self.connect():
            value_status = {'uid': migration.uid}
            res = requests.post(f"{self.host}/api/status", data=value_status)
            res_status = res.json()
            for rs in res_status:
                status = rs.get('status')
                current_version = res.get('current_version')
                migration.current_version = current_version
                if status == 'running':
                    migration.action_running()
                elif status == 'done':
                    migration.action_done()
                elif status == 'failed':
                    migration.action_failed()

    def action_get_logs(self, migration):
        if self.connect():
            type_logs = ['INFO', 'WARNING', 'ERROR']
            for ttype in type_logs:
                data = {'uid': migration.uid, 'type': ttype}
                res = requests.get(f"{self.host}/api/logs", data=data)
                res_logs = res.json()
                if ttype == 'INFO':
                    migration.log_info = res_logs
                elif ttype == 'WARNING':
                    migration.log_warning = res_logs
                elif ttype == 'ERROR':
                    migration.log_error = res_logs

    def action_get_dump(self, migration):
        if self.connect():
            res = requests.get(f"{self.host}/api/dump{migration.uid}")
            database = migration.database_id.copy()
            database.version = migration.current_version
            database.status = migration.state == 'done' and 'ok' or 'ko'
            database.backup_file = res.content
