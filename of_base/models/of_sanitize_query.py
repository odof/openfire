# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSanitizeQuery(models.Model):
    _name = 'of.sanitize.query'

    query_if = fields.Char()
    query = fields.Char(required=True)
