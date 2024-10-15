# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    auto_service_template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template',
        string=u"Modèle d'intervention pour la création automatique de DI",
        help=u"Modèle d'intervention à utiliser lors de l'activation de la création auto de DI via des mails entrants")

    @api.multi
    def set_auto_service_template_id(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'auto_service_template_id', self.auto_service_template_id.id or False)
