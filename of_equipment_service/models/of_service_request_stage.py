# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFServiceRequestStage(models.Model):
    _inherit = 'of.service.request.stage'

    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('open', "Open"),
            ('pending', "Pending"),
            ('done', "Done"),
            ('cancelled', "Cancelled"),
        ],
    )
