# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    of_used_for_phone = fields.Boolean(string="Used for phone numbers", default=True)
