# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IrConfigParameter(models.Model):
    """
    Classe Model qui hérite de la configuration de paramètre
    pour rajouter un delay entre le début et la fin de publication
    """

    _inherit = 'ir.config_parameter'
