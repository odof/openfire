# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfPanneWizard(models.TransientModel):
    _name = "of.panne.wizard"

    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe", required=True)

    def select_team(self):
        test = self._intervention_fields(self.env['of.panne'].browse(self._context.get('active_ids')), self.equipe_id)
        self.env['of.panne'].browse(self._context.get('active_ids')).write({'equipe_id': self.equipe_id.id, 'state': 'doing'})

    def _intervention_fields(self, panne, equipe):
        return {'address_id' : panne.partner_id,
                'tache_id' : panne.tache_id,  # Not null
                'user_id' : self.create_uid,
                'company_id' : self.create_uid.company_id,
                'verif_dispo' : False,
                'equipe_id' : equipe,  # Not null
                'duree' : panne.tache_id.duree,  # Not null
                'hor_md' : equipe.hor_md,  # Not null
                'hor_mf' : equipe.hor_mf,  # Not null
                'hor_ad' : equipe.hor_ad,  # Not null
                'hor_af' : equipe.hor_af,  # Not null
                'description' : panne.notes,
                'date' : fields.Datetime.to_string(fields.Datetime.now()),  # Not null
                'name' : panne.name,  # Not null
                'model_id' : panne.model_id,
                'parc_installe_id' : panne.parc_installe_id,
            }

