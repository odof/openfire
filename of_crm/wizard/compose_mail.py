# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_dict_values(self, o, objects=None):
        if not objects:
            objects = self._get_objects(o)
        result = super(OfComposeMail, self)._get_dict_values(o, objects=objects)

        partner = objects.get('partner')
        result['c_prospecteur'] = partner and partner.of_prospecteur_id and partner.of_prospecteur_id.name or ''
        return result
