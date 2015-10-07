# -*- coding: utf-8 -*-
##############################################################################
#
#   OpenERP, Open Source Management Solution
#   Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#   $Id$
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# Migration ok

from openerp.osv import fields, osv

class wizard_change_active_product(osv.TransientModel):
    """Active/désactive tous produits selectionnes"""
    _name = 'wizard.change.active.product'
    _description = "Active/desactive tous produits selectionnes"
    _columns={
        'action': fields.selection([("active","Active les produits sélectionnés"),("desactive","Désactive les produits sélectionnés")], 'Action', required=True),
    }
   
    def action_change_active_product(self, cr, uid, ids, context=None):
        """Action appelee pour activer/desactiver les produits selectionnes"""
        if not isinstance(ids, list):
            ids = [ids]
        
        product_ids = context.get('active_ids', []) # Les id des produits sélectionnés
        
        # Teste si au moins un produit est sélectionné
        if not product_ids:
            raise osv.except_osv(('Erreur ! (#AP105)'), "Vous devez sélectionner au moins un produit.")
             
        wizard = self.browse(cr, uid, ids[0], context=context) # Données du wizard
        
        if wizard.action == 'active':
            actif = True
        else:
            actif = False
            
        # Cette fonction peut être appelée de la page produits templates ou des variantes.
        # On récupère l'objet (product_template ou product_product) à modifier dans le contexte.
        self.pool[context.get('active_model', [])].write(cr, uid, product_ids, {'active': actif})
        
        return {'type': 'ir.actions.act_window_close'}


