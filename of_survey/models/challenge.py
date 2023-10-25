# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Challenge(models.Model):
    _inherit = 'gamification.challenge'

    challenge_category = fields.Selection(
        selection_add=[('certification', 'Certifications')], ondelete={'certification': 'set default'}
    )
