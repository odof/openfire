# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    of_service_mgmt = fields.Selection(
        selection=[("no", "Do not create SR"), ("sale", "Create an SR by sale order")],
        string="Follow-up of service requests",
        required=True,
        default="no",
    )
    of_intervention_template_id = fields.Many2one(
        comodel_name="of.planning.intervention.template",
        string="Associated intervention template",
    )
