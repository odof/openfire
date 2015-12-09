# -*- coding: utf-8 -*-

from openerp import models, api

# Ajout des champs specifiques du SAV Winterhalter
class of_compose_mail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_dict_values(self, data, o, objects=None):
        if not objects:
            objects = self._get_objects(o, data)
        result = super(of_compose_mail,self)._get_dict_values(data, o, objects)

        sav = objects.get('sav',[])
        if sav:
            result.update({
                'pi_of_actions_realisees' : sav.of_actions_realisees or '',
                'pi_of_actions_eff'       : sav.of_actions_eff or '',
            })
        return result
