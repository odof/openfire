# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    @api.model
    def default_get(self, field_list):
        result = super(OFPlanningIntervention, self).default_get(field_list)
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
