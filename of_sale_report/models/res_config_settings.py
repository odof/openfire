from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    of_report_type = fields.Selection(
        [('fabricant', "Rapports fabricant"), ('revendeur', "Rapports revendeur"), ('tous', "Tous les rapports")],
        string="(OF) Type de rapports",
        required=True,
        default='tous',
        help="Donne l'accès aux rapport sur mesure",
    )

    of_sale_order_installation_date_control = fields.Boolean(
        string="(OF) Contrôle de date de pose", help="Activer le contrôle de date de pose à la validation des commandes"
    )
