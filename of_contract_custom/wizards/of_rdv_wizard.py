# -*- coding: utf-8 -*-

# 1: imports of python lib
# 2: imports of odoo
from odoo import api, models, fields
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    @api.multi
    def get_values_intervention_create(self):
        vals = super(OfTourneeRdv, self).get_values_intervention_create()
        if self.service_id and self.service_id.contract_line_id:
            vals.update({
                'contract_line_id': self.service_id.contract_line_id.id
            })
        return vals
