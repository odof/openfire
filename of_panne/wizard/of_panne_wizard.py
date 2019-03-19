# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfPanneWizard(models.TransientModel):
    _name = "of.panne.wizard"

    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe", required=True)

    def select_team(self):
        vals = self.intervention_fields(self.env['of.panne'].browse(self._context.get('active_ids')), self.equipe_id, self.create_uid)
        intervention = self.env['of.planning.intervention'].create(vals)
        self.env['of.panne'].browse(self._context.get('active_ids')).write({'equipe_id': self.equipe_id.id, 'state': 'doing', 'intervention_id': intervention.id})

    def intervention_fields(self, panne, equipe, user):
        return {'address_id' : panne.partner_id.id,
                'tache_id' : panne.tache_id.id,  # Not null
                'user_id' : user.id,
                'company_id' : user.company_id.id,
                'verif_dispo' : False,
                'equipe_id' : equipe.id,  # Not null
                'duree' : panne.tache_id.duree,  # Not null
                'hor_md' : equipe.hor_md,  # Not null
                'hor_mf' : equipe.hor_mf,  # Not null
                'hor_ad' : equipe.hor_ad,  # Not null
                'hor_af' : equipe.hor_af,  # Not null
                'description' : panne.notes,
                'date' : fields.Datetime.now(),  # Not null
                'name' : panne.name,  # Not null
                'model_id' : panne.intervention_model_id.id,
                'parc_installe_id' : panne.parc_installe_id.id,
                'state': 'confirm',
                'panne_id': panne.id,
            }

