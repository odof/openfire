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

from openerp import models, fields, api, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError

class wizard_change_active_product(models.TransientModel):
    u"""Active/désactive tous produits selectionnes"""
    _name = 'wizard.change.active.product'
    _description = u"Active/désactive tous produits selectionnés"

    action = fields.Selection([
            ("active",u"Active les produits sélectionnés"),
            ("desactive",u"Désactive les produits sélectionnés")
        ], string='Action', required=True)

    @api.multi
    def action_change_active_product(self):
        u"""Action appelée pour activer/desactiver les produits selectionnés"""
        product_ids = self._context.get('active_ids', []) # Les id des produits sélectionnés
        
        # Teste si au moins un produit est sélectionné
        if not product_ids:
            raise UserError(u"Vous devez sélectionner au moins un produit.")

        actif = self.action == 'active'

        # Cette fonction peut être appelée de la page produits templates ou des variantes.
        # On récupère l'objet (product_template ou product_product) à modifier dans le contexte.
        products = self.env[self._context['active_model']].browse(product_ids)
        products.write({'active': actif})

        return {'type': 'ir.actions.act_window_close'}
