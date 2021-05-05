# -*- coding: utf-8 -*-

from odoo import api, models

class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    @api.multi
    def get_values_intervention_create(self):
        """
        :return: dictionnaires de valeurs pour la création du RDV Tech
        """
        res = super(OfTourneeRdv, self).get_values_intervention_create()
        if isinstance(res, dict) and self.service_id.equipement_id:
            res['equipement_id'] = self.service_id.equipement_id.id
        return res
