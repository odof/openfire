# -*- coding: utf-8 -*-

from openerp import models, api

# Pour la génération de pdf depuis le SAV
class of_compose_mail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o, data):
        result = super(of_compose_mail,self)._get_objects(o, data)
        if o._model._name == 'project.issue':
            result['sav'] = o
        return result

    @api.model
    def _get_dict_values(self, data, o, objects=None):
        if not objects:
            objects = self._get_objects(o, data)
        result = super(of_compose_mail,self)._get_dict_values(data, o, objects)

        sav = objects.get('sav')
        if sav:
            result.update({
                'pi_of_code'              : sav.of_code,
                'pi_name'                 : sav.name or '',  
                'pi_description'          : sav.description or '',
            })
        return result
