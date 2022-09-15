# -*- coding: utf-8 -*-

# 1: imports of python lib
# 2: imports of odoo
from odoo import models, fields, api
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    group_contract_automatic_sequence = fields.Boolean(
        string=u"(OF) Utiliser une séquence automatique pour les contrats",
        implied_group='of_contract_custom.group_contract_automatic_sequence',
        group='base.group_portal,base.group_user,base.group_public',
        help=u"Permet l'affectaton automatique d'un numéro pour la référence de vos contrats")
