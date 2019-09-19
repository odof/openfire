# -*- coding: utf-8 -*-

from odoo import models, api

class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o):
        result = super(OfComposeMail,self)._get_objects(o)
        parc = False
        if o._name == 'of.parc.installe':
            parc = o
        elif o._name == 'project.issue':
            parc = o.of_produit_installe_id

        if parc:
            result['parc_installe'] = parc
            result['address_pose'] = parc.site_adresse_id or parc.client_id

        return result

    @api.model
    def _get_dict_values(self, o, objects):
        result = super(OfComposeMail,self)._get_dict_values(o, objects)

        sav = objects.get('sav')
        parc = objects.get('parc_installe')
        product = (parc and parc.product_id) or (sav and sav.product_name_id)
        result.update({
            'pi_produit_installe': parc and parc.name or '',
            'pi_name'            : parc and parc.name or '',
            'pi_marque'          : product and ('brand_id' in product._fields) and product.brand_id.name or '',
            'pi_product_name'    : product and product.name_get()[0][1] or '',
        })
        return result
