# -*- coding: utf-8 -*-

# 1: imports of python lib
# 2: imports of odoo
from odoo import models, fields, api
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class OfSecteur(models.Model):
    _inherit = 'of.secteur'

    partner_id = fields.Many2one(comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]")
