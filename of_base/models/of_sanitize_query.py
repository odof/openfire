# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSanitizeQuery(models.Model):
    """Query to sanitize database during restore"""

    _name = 'of.sanitize.query'
    _description = "Sanitize Query"

    query_if = fields.Char()
    query = fields.Char(required=True)
