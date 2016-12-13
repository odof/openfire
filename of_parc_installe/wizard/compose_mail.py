# -*- coding: utf-8 -*-

from openerp import models, api

class of_compose_mail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o, data):
        result = super(of_compose_mail,self)._get_objects(o, data)
        parc = False
        if o._model._name == 'of.parc.installe':
            parc = o
        elif o._model._name == 'project.issue':
            parc = o.of_produit_installe_id

        if parc:
            result['parc_installe'] = parc
            result['address_pose'] = parc.site_adresse_id or parc.client_id

        return result

    @api.model
    def _get_dict_values(self, data, o, objects=None):
        if not objects:
            objects = self._get_objects(o, data)
        result = super(of_compose_mail,self)._get_dict_values(data, o, objects)

        sav = objects.get('sav')
        parc = objects.get('parc_installe')
        result.update({
            'pi_produit_installe': parc and parc.name or '',
            'pi_name'            : parc and parc.name or '',
            'pi_product_name'    : sav and sav.product_name_id and sav.product_name_id.name_get()[0][1] or '',
        })
        return result
