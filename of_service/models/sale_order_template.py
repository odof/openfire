# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    of_service_mgmt = fields.Selection(
        selection=[("no", "Ne pas créer de DI"), ("sale", "Créer une DI par bon de commande")],
        string="Suivi des demandes d'intervention",
        default="no",
    )
    of_intervention_template_id = fields.Many2one(
        comodel_name="of.planning.intervention.template",
        string="Modèle d’intervention associé",
    )
