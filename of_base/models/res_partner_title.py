# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'
    _order = 'sequence, name'

    sequence = fields.Integer(default=1, help="Used to order titles. Lower is better.")
    of_used_for_phone = fields.Boolean(string="Used for phone numbers", default=True)
