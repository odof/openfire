# -*- coding: utf-8 -*-

from odoo import models, fields, api


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
         ('list', u"plusieurs choix, plusieurs réponses possibles"),
         ('photo', u"Photo"),
         ('drawing', u"Dessin")],
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
    photo = fields.Boolean(string=u"Photo", help=u"Indique si une photo peut être jointe à la réponse")
    photo_required = fields.Boolean(
        string=u"Photo requise", help=u"Indique si une photo doit obligatoirement être jointe à la réponse")
    visibility = fields.Selection(
        selection=[('always', u"Toujours"), ('condition_met', u"Si condition vérifiée")], string=u"Visibilité")

    @api.depends('answer_ids', 'answer_type')
    def _compute_answer(self):
        for line in self:
            if line.answer_type in ('one', 'list'):
                line.answer = ', '.join([answer.name for answer in line.answer_ids])
            elif line.answer_type == 'bool':
                line.answer = 'Oui, Non'
            elif line.answer_type == 'text':
                line.answer = 'Texte libre'
            elif line.answer_type == 'photo':
                line.answer = u"Photo"
            elif line.answer_type == 'drawing':
                line.answer = u"Dessin"

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

    name = fields.Char(string="Réponse", required=True)
    planning_question_ids = fields.Many2many(
        'of.planning.intervention.question', relation="of_planning_question_reponse_rel",
        column1='answer_id', column2='question_id')

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


class OfQuestionnaireLineCategory(models.Model):
    _name = "of.questionnaire.line.category"

    name = fields.Char(string=u"Catégorie")
    sequence = fields.Integer(string=u"Séquence", default=10)
    description = fields.Text(string="Description")


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    @api.model_cr_context
    def _auto_init(self):
        view = self.env.ref(
            'of_questionnaire.of_repondre_questionnaire_planning_intervention_view_form', raise_if_not_found=False)
        if view:
            view.unlink()
        res = super(OfPlanningIntervention, self)._auto_init()
        return res

    question_ids = fields.One2many('of.planning.intervention.question', 'intervention_id', string="Questions")
    questionnaire_id = fields.Many2one('of.questionnaire', string="Questionnaire")

    @api.model
    def _get_question_vals(self, question, parc_id=False):
        return {
            'name': question.name,
            'sequence': question.sequence,
            'answer_type': question.answer_type,
            'possible_answer': question.answer,
            'category_id': question.category_id.id,
            'intervention_id': self.id,
            'type': question.type,
            'answer_ids': [(4, answer.id) for answer in question.answer_ids],
            'parc_installe_id': parc_id,
            'definitive_answer': parc_id and question.definitive_answer,
            'id_code': question.id_code,
            'condition': question.condition,
            'condition_code': question.condition_code,
            'photo': question.photo,
            'photo_required': question.photo_required,
        }

    @api.onchange('questionnaire_id')
    def onchange_questionnaire(self):
        # Charger toutes les questions qui n'ont pas d'id_code et celles dont l'id_code n'est pas déjà présent,
        # pour ne pas avoir de problèmes avec la contrainte d'unicité au moment de sauvegarder
        for question in self.questionnaire_id.line_ids.filtered(
                lambda q: not q.id_code or q.id_code not in self.question_ids.mapped('id_code')):
            vals = self._get_question_vals(question)
            self.question_ids.new(vals)
        self.questionnaire_id = False

    @api.onchange('template_id')
    def onchange_template(self):
        # Charger toutes les questions qui n'ont pas d'id_code et celles dont l'id_code n'est pas déjà présent,
        # pour ne pas avoir de problèmes avec la contrainte d'unicité au moment de sauvegarder
        for question in self.template_id.question_ids.filtered(
                lambda q: not q.id_code or q.id_code not in self.question_ids.mapped('id_code')):
            vals = self._get_question_vals(question)
            self.question_ids.new(vals)

    @api.onchange('parc_installe_id')
    def onchange_parc(self):
        # Charger toutes les questions qui n'ont pas d'id_code et celles dont l'id_code n'est pas déjà présent,
        # pour ne pas avoir de problèmes avec la contrainte d'unicité au moment de sauvegarder
        for question in self.parc_installe_id.question_ids.filtered(
                lambda q: not q.id_code or q.id_code not in self.question_ids.mapped('id_code')):
            vals = self._get_question_vals(question, question.id)
            self.question_ids.new(vals)

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
                    question_categories[question.category_id.name][1].append(
                        (question.name, question.definitive_answer))
            return sorted(question_categories.items(), key=lambda data: data[1][0])
        else:
            return []


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
    definitive_answer = fields.Text(string=u"Réponse")
    intervention_id = fields.Many2one('of.planning.intervention', string="Intervention")
    parc_installe_id = fields.Many2one('of.parc.installe.question', string=u"Équipement")
    attachment_answer = fields.Binary(string=u"Fichier réponse", attachment=True)
    attachment_answer_name = fields.Char(string=u"Nom du fichier réponse")
    condition_unmet = fields.Boolean(string=u"Condition non respectée")

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
            'possible_answer': question.answer,
            'category_id': question.category_id.id,
            'parc_installe_id': self.id,
            'type': question.type,
            'answer_ids': [(4, answer.id) for answer in question.answer_ids],
            'id_code': question.id_code,
            'condition': question.condition,
            'condition_code': question.condition_code,
            'photo': question.photo,
            'photo_required': question.photo_required,
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
    attachment_answer = fields.Binary(string=u"Fichier réponse", attachment=True)
    attachment_answer_name = fields.Char(string=u"Nom du fichier réponse")

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
