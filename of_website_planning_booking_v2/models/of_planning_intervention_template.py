# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    website_published = fields.Boolean(string=u"Publié pour le site web")
    website_name = fields.Char(string=u"Libellé site web")

    @api.multi
    def toggle_web(self):
        self.ensure_one()
        self.website_published = not self.website_published
