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
    category_id = fields.Many2one('of.questionnaire.line.category', string=u"Catégorie")

class OfQuestionnaireLineCategory(models.Model):
    _name = "of.questionnaire.line.category"

    name = fields.Char(string=u"Catégorie")
    sequence = fields.Integer(string=u"Séquence", default=10)
    description = fields.Text(string="Description")

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    question_ids = fields.One2many('of.planning.intervention.question', 'intervention_id', string="Questions")

    @api.onchange('model_id', 'parc_installe_ids')
    def onchange_questionnaire(self):
        new_ids = []
        for question in self.model_id.question_ids:
            vals = {'name': question.name,
                    'sequence': question.sequence,
                    'answer_type': question.answer_type,
                    'possible_answer': question.answer,
                    'category_id': question.category_id.id,
                    'intervention_id': self.id,
                    'type': question.type,
                }
            new_ids.append((0, 0, vals))
        for parc_installe in self.parc_installe_ids:
            for question in parc_installe.question_ids:
                vals = {'name': question.name,
                        'sequence': question.sequence,
                        'answer_type': question.answer_type,
                        'possible_answer': question.answer,
                        'category_id': question.category_id.id,
                        'intervention_id': self.id,
                        'type': question.type,
                        'parc_installe_id': parc_installe.id,
                    }
                new_ids.append((0, 0, vals))
        self.question_ids = new_ids

class OfPlanningInterventionModel(models.Model):
    _inherit = "of.planning.intervention.model"

    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.Many2many('of.questionnaire.line', related="questionnaire_id.line_ids", string="Questions", readonly=True)

class OfPlanningInterventionQuestion(models.Model):
    _name="of.planning.intervention.question"
    _order= "type, sequence"

    name = fields.Char(string="Question", required=True)
    sequence = fields.Integer(string=u"Séquence")
    answer_type = fields.Selection([('bool', "Oui/Non"),
                                    ('text', "Texte libre"),
                                    ('one', u"Plusieurs choix, une seule réponse possible"),
                                    ('list', u"plusieurs choix, plusieurs réponses possibles")], string="Type de réponse", default='bool', required=True)
    possible_answer = fields.Text(string=u"Réponses possibles")
    category_id = fields.Many2one('of.questionnaire.line.category', string=u"Catégorie")
    definitive_answer = fields.Text(string=u"Réponse")
    type = fields.Selection([('intervention', "Question d'intervention"),
                             ('product', u"Question d'équipement")], required=True, string="Type de question")
    intervention_id = fields.Many2one('of.planning.intervention', string="Intervention")
    parc_installe_id = fields.Many2one('of.parc.installe', string=u"Équipement")

class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.Many2many('of.questionnaire.line', related="questionnaire_id.line_ids", string="Questions", readonly=True)
