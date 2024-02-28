from odoo import api, fields, models


class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    @api.multi
    def get_values_intervention_create(self):
        vals = super(OfTourneeRdv, self).get_values_intervention_create()
        vals['parc_installe_id'] = self.service_id.parc_installe_id.id
        return vals
