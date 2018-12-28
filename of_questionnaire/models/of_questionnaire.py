# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfQuestionnaire(models.Model):
    _name = "of.questionnaire"

    name = fields.Char(string="Nom")
    type = fields.Selection([('intervention', "Questionnaire d'intervention"),
                             ('product', u"Questionnaire d'équipement")], required=True, default='intervention', string="Type de questionnaire")
    line_ids = fields.Many2many('of.questionnaire.line', string="Questions", order="sequence")

class OfQuestionnaireLine(models.Model):
    _name = "of.questionnaire.line"
    _order = "sequence"


    name = fields.Char(string="Question", required=True)
    sequence = fields.Integer(string=u"Séquence")
    type = fields.Selection([('intervention', "Question d'intervention"),
                             ('product', u"Question d'équipement")], required=True, string="Type de question")
    answer_type = fields.Selection([('bool', "Oui/Non"),
                                    ('text', "Texte libre"),
                                    ('one', u"Plusieurs choix, une seule réponse possible"),
                                    ('list', u"plusieurs choix, plusieurs réponses possibles")], string="Type de réponse", default='bool', required=True)
    answer = fields.Text(string=u"Réponses possibles")

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.One2many('of.planning.intervention.question', 'intervention_id', string="Questions")

    @api.multi
    def write(self, values):
        res = super(OfPlanningIntervention, self).write(values)
        return res

    @api.onchange('questionnaire_id')
    def onchange_questionnaire(self):
        new_ids = []
        for question in self.questionnaire_id.line_ids:
            vals = {'name': question.name,
                    'sequence': question.sequence,
                    'answer_type': question.answer_type,
                    'possible_answer': question.answer,
                    'intervention_id': self.id,
                }
            new_ids.append((0, 0, vals))
        self.question_ids = new_ids

class OfPlanningInterventionQuestion(models.Model):
    _name="of.planning.intervention.question"

    name = fields.Char(string="Question", required=True)
    sequence = fields.Integer(string=u"Séquence")
    answer_type = fields.Selection([('bool', "Oui/Non"),
                                    ('text', "Texte libre"),
                                    ('one', u"Plusieurs choix, une seule réponse possible"),
                                    ('list', u"plusieurs choix, plusieurs réponses possibles")], string="Type de réponse", default='bool', required=True)
    possible_answer = fields.Text(string=u"Réponses possibles")
    definitive_answer = fields.Text(string=u"Réponse")
    intervention_id = fields.Many2one('of.planning.intervention', string="Intervention")
