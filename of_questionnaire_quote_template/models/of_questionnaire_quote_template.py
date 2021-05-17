# -*- coding: utf-8 -*-

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


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    @api.model
    def default_get(self, field_list):
        result = super(OfPlanningIntervention, self).default_get(field_list)
        # Si le RDV est lié à une commande, que cette commande possède un modèle de devis
        # et que ce modèle de devis est lié à un modèle d'intervention, charger le modèle d'intervention
        # les onchanges s'occuperont de charger la tâche et le questionnaire
        if 'order_id' in result:
            order = self.env['sale.order'].browse(result['order_id'])
            if order.of_template_id and order.of_template_id.of_intervention_template_id:
                result['template_id'] = order.of_template_id.of_intervention_template_id.id
        return result

    @api.onchange('order_id')
    def _onchange_order_id(self):
        self.ensure_one()
        order = self.order_id
        if order and order.of_template_id and order.of_template_id.of_intervention_template_id:
            self.template_id = order.of_template_id.of_intervention_template_id
