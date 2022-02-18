# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    # Parc installe
    fi_parc_type_conduit = fields.Boolean(string="Type de conduit")
    fi_parc_type_air = fields.Boolean(string=u"Type d'arrivée d'air")

    # Parc installe - base of_service_parc_installe
    ri_parc_type_conduit = fields.Boolean(string="Type de conduit")
    ri_parc_type_air = fields.Boolean(string=u"Type d'arrivée d'air")
