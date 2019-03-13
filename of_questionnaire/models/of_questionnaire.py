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
    answer = fields.Text(string=u"Réponses possibles", compute='_compute_answer')
    category_id = fields.Many2one('of.questionnaire.line.category', string=u"Catégorie")
    answer_ids = fields.Many2many(comodel_name='of.questionnaire.line.reponse', column1='question_id', column2='answer_id',string=u'Réponses possibles')

    @api.depends('answer_ids', 'answer_type')
    def _compute_answer(self):
        for line in self:
            if line.answer_type in ('one', 'list'):
                line.answer = ', '.join([answer.name for answer in line.answer_ids])
            elif line.answer_type == 'bool':
                line.answer = 'Oui, Non'
            else:
                line.answer = 'Texte libre'

class OfQuestionnaireLineReponse(models.Model):
    _name = "of.questionnaire.line.reponse"

    name = fields.Char(string="Réponse", required=True)
    planning_question_ids = fields.Many2many('of.planning.intervention.question', relation="of_planning_question_reponse_rel", column1='answer_id', column2='question_id')

class OfQuestionnaireLineCategory(models.Model):
    _name = "of.questionnaire.line.category"

    name = fields.Char(string=u"Catégorie")
    sequence = fields.Integer(string=u"Séquence", default=10)
    description = fields.Text(string="Description")

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    question_ids = fields.One2many('of.planning.intervention.question', 'intervention_id', string="Questions")
    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")

    @api.model
    def _get_question_vals(self, question, parc_id=False):
        return {'name': question.name,
                'sequence': question.sequence,
                'answer_type': question.answer_type,
                'possible_answer': question.answer,
                'category_id': question.category_id.id,
                'intervention_id': self.id,
                'type': question.type,
                'answer_ids': [(4, answer.id) for answer in question.answer_ids],
                'parc_installe_id': parc_id,
                'definitive_answer': parc_id and question.definitive_answer,
            }

    @api.onchange('questionnaire_id')
    def onchange_questionnaire(self):
        for question in self.questionnaire_id.line_ids:
            vals = self._get_question_vals(question)
            self.question_ids.new(vals)
        self.questionnaire_id = False


    @api.onchange('model_id', 'parc_installe_id')
    def onchange_model_or_parc(self):
        new_ids = []
        for question in self.model_id.question_ids:
            vals = self._get_question_vals(question)
            new_ids.append((0, 0, vals))
        for question in self.parc_installe_id.question_ids:
            vals = self._get_question_vals(question, question.id)
            new_ids.append((0, 0, vals))
        self.question_ids = new_ids

    @api.multi
    def _filter_answers_category(self, questions):
        self.ensure_one()
        if questions:
            question_categories = {}
            for question in questions:
                if not question.category_id:
                    if 'uncategorized' not in question_categories:
                        question_categories['uncategorized'] = (1000, [])
                    question_categories['uncategorized'][1].append((question.name, question.definitive_answer))
                else:
                    if question.category_id.name not in question_categories:
                        question_categories[question.category_id.name] = (question.category_id.sequence, [])
                    question_categories[question.category_id.name][1].append((question.name, question.definitive_answer))
            return sorted(question_categories.items(), key=lambda data: data[1][0], reverse=False)
        else:
            return []

    @api.multi
    def write(self, vals):
        return super(OfPlanningIntervention, self).write(vals)

class OfPlanningInterventionModel(models.Model):
    _inherit = "of.planning.intervention.template"

    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.Many2many('of.questionnaire.line', related="questionnaire_id.line_ids", string="Questions", readonly=True)

class OfPlanningInterventionQuestion(models.Model):
    _name = "of.planning.intervention.question"
    _order = "type, sequence"

    name = fields.Char(string="Question", required=True)
    sequence = fields.Integer(string=u"Séquence")
    answer_type = fields.Selection([('bool', "Oui/Non"),
                                    ('text', "Texte libre"),
                                    ('one', u"Plusieurs choix, une seule réponse possible"),
                                    ('list', u"plusieurs choix, plusieurs réponses possibles")],
                                   string="Type de réponse",
                                   default='bool',
                                   required=True)
    answer = fields.Text(string=u"Réponses possibles", compute='_compute_answer')
    category_id = fields.Many2one('of.questionnaire.line.category', string=u"Catégorie")
    definitive_answer = fields.Text(string=u"Réponse")
    type = fields.Selection([('intervention', "Question d'intervention"),
                             ('product', u"Question d'équipement")], required=True, string="Type de question")
    intervention_id = fields.Many2one('of.planning.intervention', string="Intervention")
    parc_installe_id = fields.Many2one('of.parc.installe.question', string=u"Équipement")
    answer_ids = fields.Many2many(comodel_name='of.questionnaire.line.reponse', relation="of_planning_question_reponse_rel", column1='question_id', column2='answer_id', string=u'Réponses possibles')

    @api.depends('answer_ids', 'answer_type')
    def _compute_answer(self):
        for line in self:
            if line.answer_type in ('one', 'list'):
                line.answer = ', '.join([answer.name for answer in line.answer_ids])
            elif line.answer_type == 'bool':
                line.answer = 'Oui, Non'
            else:
                line.answer = 'Texte libre'

    @api.multi
    def write(self, vals):
        question_parc = not self._context.get('no_recursive') and self.filtered('parc_installe_id') or False
        other = question_parc and self - question_parc or self
        if question_parc:
            nVals = {}
            for key in ['parc_installe_id', 'intervention_id']:
                val = vals.pop(key, False)
                if val:
                    nVals[key] = val
            if nVals:  # nvals est utilisé pour mettre à jour les informations qui ne sont pas reprises dans la question du parc installé
                super(OfPlanningInterventionQuestion, question_parc).write(nVals)
            question_parc.mapped('parc_installe_id').write(vals)
        super(OfPlanningInterventionQuestion, other).write(vals)
        return True

class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.One2many('of.parc.installe.question', 'parc_installe_id', string="Questions")

    @api.model
    def _get_question_vals(self, question):
        return {'name': question.name,
                'sequence': question.sequence,
                'answer_type': question.answer_type,
                'possible_answer': question.answer,
                'category_id': question.category_id.id,
                'parc_installe_id': self.id,
                'type': question.type,
                'answer_ids': [(4, answer.id) for answer in question.answer_ids],
            }

    @api.onchange('questionnaire_id')
    def onchange_questionnaire(self):
        for question in self.questionnaire_id.line_ids:
            vals = self._get_question_vals(question)
            self.question_ids.new(vals)
        self.questionnaire_id = False

class OfParcInstalleQuestion(models.Model):
    _name = "of.parc.installe.question"
    _inherit = "of.questionnaire.line"
    _order = "type, sequence"

    definitive_answer = fields.Text(string=u"Réponse")
    parc_installe_id = fields.Many2one('of.parc.installe', string=u"Équipement")
    planning_question_ids = fields.One2many('of.planning.intervention.question', 'parc_installe_id')
    answer_ids = fields.Many2many(comodel_name='of.questionnaire.line.reponse',
                                  relation="of_parc_question_reponse_rel", column1='question_id',
                                  column2='answer_id', string=u'Réponses possibles')

    @api.multi
    def write(self, vals):
        self = self.with_context(no_recursive=True)
        ret = super(OfParcInstalleQuestion, self).write(vals)
        for key in ['parc_installe_id', 'planning_question_ids']:
            vals.pop(key, False)
        self.planning_question_ids.write(vals)
        return ret
