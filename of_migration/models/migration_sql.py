# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MigrationSQL(models.Model):
    _name = 'migration.sql'

    name = fields.Char()
    version = fields.Integer()
    subversion = fields.Integer()
    pre_script = fields.Text()
    post_script = fields.Text()
