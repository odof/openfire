# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CRMStage(models.Model):
    _inherit = "crm.stage"

    of_auto_model_name = fields.Selection(selection_add=[("sale.order", "Sale Order")])
