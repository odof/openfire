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

    model_id = fields.Many2one('of.planning.intervention.model', string=u"Modèle d'intervention")
    question_ids = fields.One2many('of.planning.intervention.question', 'intervention_id', string="Questions")
    number = fields.Char(String=u"Numéro")
    calendar_name = fields.Char(string="Calendar Name", compute="_compute_calendar_name")

    @api.depends('name', 'number')
    def _compute_calendar_name(self):
        for intervention in self:
            intervention.calendar_name = intervention.number or intervention.name

    @api.multi
    def write(self, vals):
        res = super(OfPlanningIntervention, self).write(vals)
        for interv in self:
            if interv.model_id and interv.state in ('confirm', 'done', 'postponed') and not interv.number:
                interv.number = interv.model_id.sequence_id.next_by_id()
#                super(OfPlanningIntervention, interv).write({'number': interv.model_id.sequence_id.next_by_id()})
        return res

    @api.multi
    def button_confirm(self):
        ret = super(OfPlanningIntervention, self).button_confirm()
        if self.model_id:
            self.write({'number': self.model_id.sequence_id.next_by_id()})
        return ret

    @api.onchange('model_id')
    def onchange_questionnaire(self):
        new_ids = []
        for question in self.model_id.question_ids:
            vals = {'name': question.name,
                    'sequence': question.sequence,
                    'answer_type': question.answer_type,
                    'possible_answer': question.answer,
                    'category_id': question.category_id.id,
                    'intervention_id': self.id,
                }
            new_ids.append((0, 0, vals))
        self.question_ids = new_ids

class OfPlanningInterventionModel(models.Model):
    _name = "of.planning.intervention.model"

    name = fields.Char(string=u"Nom du modèle", required=True)
    active = fields.Boolean(string="Active", default=True)
    code = fields.Char(string="Code", compute="_compute_code", inverse="_inverse_code", store=True, required=True)
    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.Many2many('of.questionnaire.line', related="questionnaire_id.line_ids", string="Questions", readonly=True)
    sequence_id = fields.Many2one('ir.sequence', string=u"Séquence")

    @api.depends('sequence_id')
    def _compute_code(self):
        for intervention_model in self:
            intervention_model.code = intervention_model.sequence_id.prefix

    def _inverse_code(self):
        for intervention_model in self:
            if not intervention_model.code:
                continue
            intervention_model.sequence_id.sudo().write({'prefix': intervention_model.code})

    @api.model
    def create(self, vals):
        if not vals.get('sequence_id'):
            vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})

        intervention_model = super(OfPlanningInterventionModel, self).create(vals)
        return intervention_model

    @api.model
    def _create_sequence(self, vals, refund=False):
        """ Create new no_gap entry sequence for every new Journal"""
        seq = {
            'name': u'Séquence ' + vals['name'],
            'implementation': 'no_gap',
            'prefix': vals['code'],
            'padding': 4,
            'number_increment': 1,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)

class OfPlanningInterventionQuestion(models.Model):
    _name="of.planning.intervention.question"

    name = fields.Char(string="Question", required=True)
    sequence = fields.Integer(string=u"Séquence")
    answer_type = fields.Selection([('bool', "Oui/Non"),
                                    ('text', "Texte libre"),
                                    ('one', u"Plusieurs choix, une seule réponse possible"),
                                    ('list', u"plusieurs choix, plusieurs réponses possibles")], string="Type de réponse", default='bool', required=True)
    possible_answer = fields.Text(string=u"Réponses possibles")
    category_id = fields.Many2one('of.questionnaire.line.category', string=u"Catégorie")
    definitive_answer = fields.Text(string=u"Réponse")
    intervention_id = fields.Many2one('of.planning.intervention', string="Intervention")
