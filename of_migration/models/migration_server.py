# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
import tarfile

import pysftp
import requests

from odoo import fields, models

from odoo.addons.http_routing.models.ir_http import slugify

logger = logging.getLogger(__name__)

headers_json = {'Content-Type': 'application/json'}


class MigrationServer(models.Model):
    _name = 'migration.server'

    name = fields.Char()
    host = fields.Char()
    port = fields.Integer()
    ttype = fields.Selection([('migration', 'Migration'), ('backup', 'Backup')], string="Type")
    state = fields.Char()
    authentication_id = fields.Many2one(comodel_name='migration.authentication', string="Authentication")

    def connect(self):
        return True

    def action_start_migration(self, migration):
        if self.connect():
            migration.current_version = migration.database_id.version
            # on envoie le fichier sur le serveur distant
            if migration.database_id.backup_type == 'file':
                res = requests.post(
                    f"{self.host}:{self.port}/api/uploads",
                    data=base64.b64decode(migration.database_id.backup_file),
                )
                res_file = res.json()
            elif migration.database_id.backup_type == 'distant':
                cnopts = pysftp.CnOpts()
                cnopts.hostkeys = None
                connection = pysftp.Connection(
                    host=migration.database_id.backup_server.host.replace('https://', '').replace('http://', ''),
                    username=migration.database_id.backup_server.authentication_id.name,
                    password=migration.database_id.backup_server.authentication_id.password,
                    port=migration.database_id.backup_server.port,
                    cnopts=cnopts,
                )
                connection.get(f"/upload/{migration.database_id.backup_filename}", f"/tmp/backup{migration.id}")
                res = requests.post(
                    f"{self.host}:{self.port}/api/uploads",
                    data=open(f"/tmp/backup{migration.id}", 'rb'),
                )
                res_file = res.json()
            elif migration.database_id.backup_type == 'uuid':
                res_file = {'uid': migration.database_id.backup_uuid}

            migration.database_id.backup_uuid = res_file.get('uid')
            # on envoie les scripts s'ils n'y sont pas déjà
            for script in migration.database_id.script_ids:
                value_script = {
                    'id': script.id,
                    'name': script.name,
                    'version': script.version,
                    'sous_version': script.subversion,
                    'post_script': script.post_script,
                    'pre_script': script.pre_script,
                }
                res = requests.post(f"{self.host}:{self.port}/api/sql", json=value_script)

            value_migration = {
                'client': f"{slugify(migration.partner_id.name)}{migration.partner_id.id}",
                'debut': str(migration.start_version),
                'fin': str(migration.end_version),
                'clean_all': migration.clean_all,
                'type': migration.ttype,
                'file_uid': res_file.get('uid'),
                'scripts': migration.database_id.script_ids.ids,
            }
            logger.info(value_migration)
            res = requests.post(f"{self.host}:{self.port}/api/migration", json=value_migration, headers=headers_json)

            res_migration = res.json()
            logger.info(res.text)
            if error := res_migration.get('error'):
                logger.info(error)
                migration.action_failed()
            migration.uid = res_migration.get('uid')
            migration.action_running()

    def action_status_migration(self, migration):
        if self.connect():
            value_status = {'uid': migration.uid}
            res = requests.get(f"{self.host}:{self.port}/api/status", json=value_status)
            res_status = res.json()
            for rs in res_status:
                status = rs.get('status')
                current_version = rs.get('current_version')
                migration.current_version = current_version
                if status == 'running':
                    migration.action_running()
                elif status == 'done':
                    migration.action_done()
                elif status == 'failed':
                    migration.action_failed()

    def action_get_logs(self, migration):
        logger.info("Appel get logs")
        if self.connect():
            type_logs = ['INFO', 'WARNING', 'ERROR']
            for ttype in type_logs:
                data = {'uid': migration.uid, 'type': ttype}
                res = requests.get(f"{self.host}:{self.port}/api/logs", json=data)
                res_logs = res.json()
                if error := res_logs.get('error'):
                    logger.info(error)
                if ttype == 'INFO':
                    migration.log_info = ""
                    for log in res_logs.get('logs', []):
                        migration.log_info += str(log)
                elif ttype == 'WARNING':
                    migration.log_warning = ""
                    for log in res_logs.get('logs', []):
                        migration.log_warning += str(log)
                elif ttype == 'ERROR':
                    migration.log_error = ""
                    for log in res_logs.get('logs', []):
                        migration.log_error += str(log)

    def action_get_dump(self, migration):
        if self.connect():
            res = requests.get(f"{self.host}:{self.port}/api/dump/{migration.uid}")
            database = migration.database_id.copy()
            database.version = migration.current_version
            database.status = migration.state == 'done' and 'ok' or 'ko'
            if database.backup_type == 'file':
                database.backup_file = res.content
            elif database.backup_type == 'distant':
                database.backup_filename = f"{slugify(migration.partner_id.name)}-{database.version}.dump"
                cnopts = pysftp.CnOpts()
                cnopts.hostkeys = None
                connection = pysftp.Connection(
                    host=migration.database_id.backup_server.host.replace('https://', '').replace('http://', ''),
                    username=migration.database_id.backup_server.authentication_id.name,
                    password=migration.database_id.backup_server.authentication_id.password,
                    port=migration.database_id.backup_server.port,
                    cnopts=cnopts,
                )
                f = open(f"/tmp/{database.backup_filename}", "wb")
                f.write(res.content)
                f.close()

                connection.put(f"/tmp/{database.backup_filename}", f"/upload/{database.backup_filename}")

    def action_delete_migration(self, migration):
        res = requests.delete(f"{self.host}:{self.port}/api/migration/{migration.uid}")
