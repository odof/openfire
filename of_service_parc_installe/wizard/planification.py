# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OfPlanifCreneau(models.TransientModel):
    _inherit = 'of.planif.creneau'

    @api.multi
    def get_values_intervention_create(self):
        res = super(OfPlanifCreneau, self).get_values_intervention_create()
        service = self.selected_id.service_id
        res['parc_installe_id'] = service.parc_installe_id.id
        return res


class OfPlanifCreneauProp(models.TransientModel):
    _inherit = 'of.planif.creneau.prop'

    parc_installe_product_name = fields.Char(
        string=u"Désignation", related="service_id.parc_installe_id.product_id.name", readonly=True)
