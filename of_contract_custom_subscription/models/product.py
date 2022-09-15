# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# 1: imports of python lib
from odoo import models, fields, api
# 2: imports of odoo
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_subscription = fields.Boolean(string="Facturation par abonnement")
