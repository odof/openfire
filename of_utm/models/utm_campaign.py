# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    active = fields.Boolean(default=True)
