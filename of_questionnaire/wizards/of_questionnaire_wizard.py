# -*- coding: utf-8 -*-

from odoo import models, fields, api

class RepondreQuestionnaireWizard(models.TransientModel):
    _name = 'of.repondre.questionnaire.wizard'

    question_ids = fields.Many2many('of.planning.intervention.question', relation="of_repondre_questionnaire_question_rel")
    question_id = fields.Many2one('of.planning.intervention.question')
    answer_type = fields.Selection([('bool', "Oui/Non"),
                                    ('text', "Texte libre"),
                                    ('one', u"Plusieurs choix, une seule réponse possible"),
                                    ('list', u"plusieurs choix, plusieurs réponses possibles")], compute="_compute_type", store=True)
    question = fields.Char(related='question_id.name')
    answer_bool = fields.Selection([('Oui', 'Oui'), ('Non', 'Non')], string=u"Réponse")
    answer_id = fields.Many2one('of.questionnaire.line.reponse', string=u"Réponse")
    answer_ids = fields.Many2many('of.questionnaire.line.reponse', relation="of_repondre_questionnaire_reponse_rel", string=u"Réponses")
    answer_text = fields.Text(string=u"Réponse")

    @api.depends('question_id')
    def _compute_type(self):
        for reponse in self:
            reponse.answer_type = reponse.question_id.answer_type

    @api.model
    def _convert_question_answer(self, question):
        reponse_obj = self.env['of.questionnaire.line.reponse']
        result = {}
        if question.answer_type == 'bool':
            result['answer_bool'] = question.definitive_answer
        elif question.answer_type == 'text':
            result['answer_text'] = question.definitive_answer
        elif question.answer_type == 'one':
            reponse = reponse_obj.search([('planning_question_ids', 'in', [question.id]),
                                          ('name', '=', question.definitive_answer)], limit=1)
            result['answer_id'] = reponse.id
        elif question.answer_type == 'list':
            reponses = reponse_obj.browse([])
            if question.definitive_answer:
                for r in question.definitive_answer.split(', '):
                    reponse = reponse_obj.search([('planning_question_ids', 'in', [question.id]),
                                                  ('name', '=', r)], limit=1)
                    reponses |= reponse
            result['answer_ids'] = [(6, 0, reponses._ids)]
        return result

    @api.model
    def default_get(self, fields_list):
        rec = super(RepondreQuestionnaireWizard, self).default_get(fields_list)
        question_ids = self._context.get('question_ids', [])
        if question_ids:
            rec['question_id'] = question_ids[0][1]
            rec['question_ids'] = question_ids[1:]
            question = self.env['of.planning.intervention.question'].browse(question_ids[0][1])
            if question.definitive_answer:
                rec.update(self._convert_question_answer(question))
        return rec

    def validate_answer(self):
        if self.question_id.answer_type == 'bool':
            self.question_id.write({'definitive_answer': self.answer_bool})
        elif self.question_id.answer_type == 'text':
            self.question_id.write({'definitive_answer': self.answer_text})
        elif self.question_id.answer_type == 'one':
            self.question_id.write({'definitive_answer': self.answer_id.name})
        elif self.question_id.answer_type == 'list':
            self.question_id.write({'definitive_answer': ', '.join([answer.name for answer in self.answer_ids])})
        return self.next_question()

    def next_question(self):
        self.question_id = self.question_ids and self.question_ids[0] or False
        self.question_ids -= self.question_id
        if self.question_id:
            self.write(self._convert_question_answer(self.question_id))
            return {"type": "ir.actions.do_nothing"}
        else:
            return True
