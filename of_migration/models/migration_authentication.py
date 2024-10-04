# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MigrationAuthentication(models.Model):
    _name = 'migration.authentication'

    name = fields.Char()
    password = fields.Char()
