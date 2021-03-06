# -*- coding: utf-8 -*-

from odoo import models, api


class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_dict_values(self, o, objects):
        result = super(OfComposeMail, self)._get_dict_values(o, objects)

        partner = objects['partner']
        result['c_prospecteur'] = partner.of_prospecteur_id.name or ''
        return result
