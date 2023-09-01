# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class OfQuestionnaire(models.Model):
    _name = "of.questionnaire"

    name = fields.Char(string="Nom")
    type = fields.Selection(
        [('intervention', "Questionnaire d'intervention"), ('product', u"Questionnaire d'équipement")],
        required=True, default='intervention', string="Type de questionnaire")
    line_ids = fields.Many2many('of.questionnaire.line', string="Questions")


class OfQuestionnaireLine(models.Model):
    _name = "of.questionnaire.line"
    _order = "sequence"

    name = fields.Char(string="Question", required=True)
    sequence = fields.Integer(string=u"Séquence")
    type = fields.Selection(
        [('intervention', "Question d'intervention"), ('product', u"Question d'équipement")],
        required=True, string="Type de question")
    answer_type = fields.Selection(
        [('bool', "Oui/Non"),
         ('text', "Texte libre"),
         ('one', u"Plusieurs choix, une seule réponse possible"),
         ('list', u"plusieurs choix, plusieurs réponses possibles")],
        string="Type de réponse", default='bool', required=True)
    answer = fields.Text(string=u"Réponses possibles", compute='_compute_answer')
    category_id = fields.Many2one('of.questionnaire.line.category', string=u"Catégorie")
    answer_ids = fields.Many2many(
        comodel_name='of.questionnaire.line.reponse', column1='question_id', column2='answer_id',
        string=u'Réponses possibles')
    id_code = fields.Char(
        string=u"Code identifiant", help=u"Code identifiant de la question, à utiliser pour les conditions")
    condition = fields.Boolean(
        string=u"Condition", help=u"Indique si une condition est à respecter pour poser cette question")
    condition_code = fields.Char(string=u"Code de condition", help=u"Code à respecter pour que la question soit posée")
    print_mode = fields.Selection(selection=[
        ('always', u"Toujours"),
        ('answer', u"S'il y a une réponse"),
        ('never', u"Jamais")], string=u"Impression", required=True, default='always')
    condition_print_mode = fields.Selection(selection=[
        ('always', u"Toujours"),
        ('condition', u"Si condition vérifiée"),
        ('condition_answer', u"Si condition vérifiée, avec une réponse"),
        ('never', u"Jamais")], string=u"Impression avec condition", required=True, default='always')
    required = fields.Boolean(string=u"Question obligatoire")

    @api.depends('answer_ids', 'answer_type')
    def _compute_answer(self):
        for line in self:
            if line.answer_type in ('one', 'list'):
                line.answer = ', '.join([answer.name for answer in line.answer_ids])
            elif line.answer_type == 'bool':
                line.answer = 'Oui, Non'
            elif line.answer_type == 'text':
                line.answer = 'Texte libre'

    @api.model
    def create(self, vals):
        record = super(OfQuestionnaireLine, self).create(vals)
        self.env['of.questionnaire.line.reponse']._vacuum()
        return record

    @api.multi
    def write(self, vals):
        super(OfQuestionnaireLine, self).write(vals)
        self.env['of.questionnaire.line.reponse']._vacuum()
        return True


class OfQuestionnaireLineReponse(models.Model):
    _name = "of.questionnaire.line.reponse"
    _order = "sequence"

    name = fields.Char(string="Réponse", required=True)
    sequence = fields.Integer(string=u"Séquence")
    active = fields.Boolean(string="Active", default=True)
    planning_question_ids = fields.Many2many(
        'of.planning.intervention.question', relation="of_planning_question_reponse_rel",
        column1='answer_id', column2='question_id', ondelete="restrict")

    @api.model
    def _vacuum(self):
        """
        Supprime les réponses non utilisées
        """
        self = self.sudo()
        cr = self.env.cr
        question_fields = self.env['ir.model.fields'].search([('relation', '=', 'of.questionnaire.line.reponse'),
                                                              ('ttype', 'in', ('many2one', 'many2many'))])
        question_ids = set(self.search([])._ids)
        for field in question_fields:
            if not question_ids:
                break
            if field.ttype == 'many2one':
                field_name = field.name
                table_name = self.env[field.model]._table
            else:
                field_name = field.column2
                table_name = field.relation_table
            cr.execute("SELECT DISTINCT %s FROM %s WHERE %s IN %%s" % (field_name, table_name, field_name),
                       (tuple(question_ids), ))
            question_ids -= set(row[0] for row in cr.fetchall())
        self.browse(question_ids).unlink()

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
        return super(OfQuestionnaireLineReponse, self).unlink()

    @api.multi
    def write(self, vals):

        if self._uid != SUPERUSER_ID and not self.env.user.has_group(
                'of_planning.group_planning_intervention_modification'):
            if self.env['of.questionnaire.line'].search([('answer_ids', 'in', self._ids)]) or \
                    self.env['of.planning.intervention.question'].search([('answer_ids', 'in', self._ids),
                                                                          ('definitive_answer', '=', False)]) or \
                    self.env['of.parc.installe.question'].search([('answer_ids', 'in', self._ids),
                                                                  ('definitive_answer', '=', False)]):
                raise UserError(u"Vous n'avez pas les droits pour modifier une réponse présente dans une question, "
                                u"une intervention ou un parc installé.")
        return super(OfQuestionnaireLineReponse, self).write(vals)


class OfQuestionnaireLineCategory(models.Model):
    _name = "of.questionnaire.line.category"

    name = fields.Char(string=u"Catégorie")
    sequence = fields.Integer(string=u"Séquence", default=10)
    description = fields.Text(string="Description")


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    question_ids = fields.One2many('of.planning.intervention.question', 'intervention_id', string="Questions")
    question_answered = fields.Boolean(
        string=u"Question answered", compute='_compute_question_answered', help=u"At least one")
    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")

    @api.depends('question_ids.definitive_answer')
    def _compute_question_answered(self):
        for interv in self:
            interv.question_answered = any(interv.question_ids.mapped('definitive_answer'))

    @api.model
    def _get_question_vals(self, question, parc_id=False):
        return {
            'name': question.name,
            'sequence': question.sequence,
            'answer_type': question.answer_type,
            'category_id': question.category_id.id,
            'intervention_id': self.id,
            'type': question.type,
            'answer_ids': [(4, answer.id) for answer in question.answer_ids],
            'parc_installe_id': parc_id,
            'definitive_answer': parc_id and question.definitive_answer,
            'id_code': question.id_code,
            'condition': question.condition,
            'condition_code': question.condition_code,
            'print_mode': question.print_mode,
            'condition_print_mode': question.condition_print_mode,
            'required': question.required,
        }

    @api.onchange('questionnaire_id')
    def onchange_questionnaire(self):
        # Charger toutes les questions qui n'ont pas d'id_code et celles dont l'id_code n'est pas déjà présent,
        # pour ne pas avoir de problèmes avec la contrainte d'unicité au moment de sauvegarder
        for question in self.questionnaire_id.line_ids.filtered(
                lambda q: not q.id_code or q.id_code not in self.question_ids.mapped('id_code')):
            vals = self._get_question_vals(question)
            if self.env.in_onchange:
                self.question_ids.new(vals)
            else:
                self.question_ids.create(vals)
        self.questionnaire_id = False

    @api.onchange('template_id')
    def onchange_template_id(self):
        super(OfPlanningIntervention, self).onchange_template_id()

        # Charger toutes les questions qui n'ont pas d'id_code et celles dont l'id_code n'est pas déjà présent,
        # pour ne pas avoir de problèmes avec la contrainte d'unicité au moment de sauvegarder
        question_line_obj = self.env['of.planning.intervention.question']
        question_line = question_line_obj
        questions_dict = {
            question.id_code: question
            for question in self.question_ids
            if question.id_code
        }
        for question in self.template_id.question_ids:
            vals = self._get_question_vals(question)
            interv_question = questions_dict.get(question.id_code)
            if interv_question:
                interv_question.update(vals)
            else:
                interv_question = question_line_obj.new(vals)
            question_line += interv_question
        self.question_ids = question_line

    @api.onchange('parc_installe_id')
    def onchange_parc_installe_id(self):
        # Charger toutes les questions qui n'ont pas d'id_code et celles dont l'id_code n'est pas déjà présent,
        # pour ne pas avoir de problèmes avec la contrainte d'unicité au moment de sauvegarder
        for question in self.parc_installe_id.question_ids.filtered(
                lambda q: not q.id_code or q.id_code not in self.question_ids.mapped('id_code')):
            vals = self._get_question_vals(question, question.id)
            if self.env.in_onchange:
                self.question_ids.new(vals)
            else:
                self.question_ids.create(vals)

    def copy(self, default=None):
        interv_new = super(OfPlanningIntervention, self).copy(default=default)
        for question in self.question_ids:
            question.copy({'intervention_id': interv_new.id})
        return interv_new

    @api.multi
    def recompute_questions_condition_unmet(self):
        for intervention in self:
            ctx = {}
            for question in intervention.question_ids:
                if question.id_code:
                    ctx[question.id_code] = question.definitive_answer
                if question.condition:
                    condition_code = question.condition_code
                    condition_code = condition_code.replace(' = ', ' == ')
                    condition_code = condition_code.replace(' et ', ' and ')
                    condition_code = condition_code.replace(' ou ', ' or ')
                    try:
                        condition_unmet = not safe_eval(condition_code, ctx)
                    except Exception:
                        condition_unmet = True
                    if condition_unmet != question.condition_unmet:
                        question.condition_unmet = condition_unmet

    @api.multi
    def _write(self, vals):
        res = super(OfPlanningIntervention, self)._write(vals)
        if vals.get('state', '') == 'done':
            self.recompute_questions_condition_unmet()
            for intervention in self:
                if any(
                        q.required and
                        not q.condition_unmet and
                        not q.has_been_answered()
                        for q in intervention.question_ids):
                    raise ValidationError(u"Au moins une question obligatoire n'a pas de réponse.")
        return res

    @api.multi
    def _filter_answers_category(self, questions):
        self.ensure_one()
        if questions:
            question_categories = {}
            for question in questions:
                if (not question.condition and
                        (question.print_mode == 'always' or
                         (question.print_mode == 'answer' and question.definitive_answer))) \
                        or (question.condition and
                            (question.condition_print_mode == 'always' or
                             (question.condition_print_mode == 'condition' and not question.condition_unmet) or
                             (question.condition_print_mode == 'condition_answer' and question.definitive_answer))):
                    if not question.category_id:
                        if u"Indéfini" not in question_categories:
                            question_categories[u"Indéfini"] = (1000, [])
                        question_categories[u"Indéfini"][1].append((question.name, question.definitive_answer))
                    else:
                        if question.category_id.name not in question_categories:
                            question_categories[question.category_id.name] = (question.category_id.sequence, [])
                        question_categories[question.category_id.name][1].append(
                            (question.name, question.definitive_answer))
            return sorted(question_categories.items(), key=lambda data: data[1][0])
        else:
            return []

    def unlink_question_ids(self):
        self.question_ids.unlink()


class OfPlanningInterventionModel(models.Model):
    _inherit = "of.planning.intervention.template"

    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.Many2many(
        'of.questionnaire.line', related="questionnaire_id.line_ids", string="Questions", readonly=True)


class OfPlanningInterventionQuestion(models.Model):
    _name = "of.planning.intervention.question"
    _inherit = "of.questionnaire.line"
    _order = "type, sequence"

    answer_ids = fields.Many2many(
        comodel_name='of.questionnaire.line.reponse', relation="of_planning_question_reponse_rel",
        column1='question_id', column2='answer_id', string=u'Réponses possibles')
    definitive_answer = fields.Text(string=u"Réponse", copy=False)
    intervention_id = fields.Many2one('of.planning.intervention', string="Intervention")
    intervention_state = fields.Selection(related='intervention_id.state')
    parc_installe_id = fields.Many2one('of.parc.installe.question', string=u"Équipement")
    condition_unmet = fields.Boolean(string=u"Condition non respectée", copy=False)

    _sql_constraints = [
        ('of_id_code_intervention_uniq', 'unique(id_code,intervention_id)',
         u"Le code identifiant des questions doit etre unique par RDV !"),
    ]

    @api.multi
    def write(self, vals):
        question_parc = not self._context.get('of_question_no_recursive') and self.filtered('parc_installe_id') or False
        other = question_parc and self - question_parc or self
        if question_parc:
            n_vals = {}
            for key in ('parc_installe_id', 'intervention_id'):
                val = vals.pop(key, False)
                if val:
                    n_vals[key] = val
            # n_vals est utilisé pour mettre à jour les informations qui ne sont pas reprises dans la question
            # du parc installé
            if n_vals:
                super(OfPlanningInterventionQuestion, question_parc).write(n_vals)
            question_parc.mapped('parc_installe_id').write(vals)
        super(OfPlanningInterventionQuestion, other).write(vals)
        return True

    @api.multi
    def has_been_answered(self):
        self.ensure_one()
        type_field = self.get_answer_field_by_type()
        return bool(self[type_field[self.answer_type]])

    @api.model
    def get_answer_field_by_type(self):
        return {
            'bool': 'definitive_answer',
            'text': 'definitive_answer',
            'one': 'definitive_answer',
            'list': 'definitive_answer',
        }


class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")
    question_ids = fields.One2many('of.parc.installe.question', 'parc_installe_id', string="Questions")

    @api.model
    def _get_question_vals(self, question):
        return {
            'name': question.name,
            'sequence': question.sequence,
            'answer_type': question.answer_type,
            'category_id': question.category_id.id,
            'parc_installe_id': self.id,
            'type': question.type,
            'answer_ids': [(4, answer.id) for answer in question.answer_ids],
            'id_code': question.id_code,
            'condition': question.condition,
            'condition_code': question.condition_code,
            'print_mode': question.print_mode,
            'condition_print_mode': question.condition_print_mode,
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
    answer_ids = fields.Many2many(
        comodel_name='of.questionnaire.line.reponse', relation="of_parc_question_reponse_rel",
        column1='question_id', column2='answer_id', string=u'Réponses possibles')

    _sql_constraints = [
        ('of_id_code_parc_installe_uniq', 'unique(id_code, parc_installe_id)',
         u"Le code identifiant des questions doit être unique par parc installé !"),
    ]

    @api.multi
    def write(self, vals):
        self = self.with_context(of_question_no_recursive=True)
        ret = super(OfParcInstalleQuestion, self).write(vals)
        for key in ['parc_installe_id', 'planning_question_ids']:
            vals.pop(key, False)
        self.planning_question_ids.write(vals)
        return ret
