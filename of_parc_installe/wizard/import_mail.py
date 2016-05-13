# -*- coding: utf-8 -*-

from openerp import models, api
from openerp.exceptions import UserError

class of_gesdoc_import(models.TransientModel):
    _inherit = 'of.gesdoc.import'

    def import_data_obj(self, data, obj):
        parc_obj = self.env['of.parc.installe']
        result = super(of_gesdoc_import, self).import_data_obj(data, obj)
        if obj._name == 'project.issue':
            parc_name = data.get('pi_produit_installe','').strip()
            if not parc_name:
                return result

            # Recherche de tous les parcs dont le numéro de série correspond
            all_parcs = parc_obj.search([('name','=ilike',parc_name)])
            if not all_parcs:
                raise UserError(u'Erreur!\n'
                                u'Aucun parc installé ne correspond au numéro de série saisi.\n'
                                u'Veuillez corriger le numéro de série ou créer le parc installé correspondant.')

            # On conserve le produit du sav si il est renseigné et correspond au numéro de série saisi ...
            product = obj.product_name_id
            parcs = [parc for parc in all_parcs if parc.product_id == product]
            if not parcs:
                # ... sinon on le remplace par le produit le plus cher pour ce numéro de série (les produits moins cher sont des composants)
                product = max(all_parcs, key=lambda parc: parc.product_id.list_price).product_id
                parcs = [parc for parc in all_parcs if parc.product_id == product]
                result['product_name_id'] = product.id

            # Pour plusieurs parcs installés, on ne garde que le plus récent
            parc = max(parcs, key=lambda parc: parc.date_service)

            result['of_produit_installe_id'] = parc.id
        return result
