# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    website_create = fields.Boolean(string=u"Créé par le site web")
