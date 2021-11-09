# -*- coding: utf-8 -*-

from odoo import api, models, fields


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
