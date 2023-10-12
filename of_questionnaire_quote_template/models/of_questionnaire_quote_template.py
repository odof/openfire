# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleQuoteTemplate(models.Model):
    _inherit = "sale.quote.template"

    of_intervention_template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template', string=u"Modèle de RDV")
    of_questionnaire_id = fields.Many2one(
        comodel_name='of.questionnaire', string=u"Questionnaire",
        related='of_intervention_template_id.questionnaire_id', readonly=True)
    of_question_ids = fields.Many2many(
        comodel_name='of.questionnaire.line', related='of_questionnaire_id.line_ids',
        string=u"Questions", readonly=True)

