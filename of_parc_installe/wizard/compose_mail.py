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
        result.update({
            'pi_produit_installe' : sav and sav.of_produit_installe_id and sav.of_produit_installe_id.name or '',
            'pi_product_name': sav and sav.product_name_id and sav.product_name_id.name_get()[0][1] or '',
        })
        return result
