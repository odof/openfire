# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    of_mobile_can_create_additional_sale = fields.Boolean(string="Can create additional sale from an intervention")
