# -*- coding: utf-8 -*-

from odoo import models, api, SUPERUSER_ID
from odoo.exceptions import UserError


class OFQuestionnaireLineReponse(models.Model):
    _inherit = "of.questionnaire.line.reponse"

    @api.multi
    def unlink(self):

        if self._uid != SUPERUSER_ID:
            if self.env['of.questionnaire.line'].search([('answer_ids', 'in', self._ids)]) or \
                    self.env['of.planning.intervention.question'].search([('answer_ids', 'in', self._ids),
                                                                          ('definitive_answer', '=', False)]) or \
                    self.env['of.parc.installe.question'].search([('answer_ids', 'in', self._ids),
                                                                  ('definitive_answer', '=', False)]):
                raise UserError(u"Seul l'administrateur peut supprimer une réponse présente dans une question, "
                                u"une intervention ou un parc installé.")
        return super(OFQuestionnaireLineReponse, self).unlink()

    @api.multi
    def write(self, vals):

        if self._uid != SUPERUSER_ID and not self.env.user.has_group('of_access_control'
                                                                     '.group_planning_intervention_manager'):
            if self.env['of.questionnaire.line'].search([('answer_ids', 'in', self._ids)]) or \
                    self.env['of.planning.intervention.question'].search([('answer_ids', 'in', self._ids),
                                                                          ('definitive_answer', '=', False)]) or \
                    self.env['of.parc.installe.question'].search([('answer_ids', 'in', self._ids),
                                                                  ('definitive_answer', '=', False)]):
                raise UserError(u"Vous n'avez pas les droits pour modifier une réponse présente dans une question, "
                                u"une intervention ou un parc installé.")
        return super(OFQuestionnaireLineReponse, self).write(vals)
