# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name" : "OpenFire Base",
    "version" : "1.1",
    "author" : "OpenFire",
    'complexity': "easy",
    "description" : """
Personnalisations des fonctions de base Odoo :

- Ajout des colonnes destinataire et partenaire dans la vue liste des emails
- Ajout onglet historique dans formulaire partenaire
- Ajoute la référence du produit dans la vue liste
- Affiche en permanence le nom de la base dans la barre de menu
- Retire la couleur de fond aléatoire de l'image mise par défaut à la création d'un partenaire
- Ajoute le groupe utilisateur "Intranet"
""",
    "website" : "www.openfire.fr",
    "depends" : ["product"], # Migration 8 vers 9 "email_template",
    "category" : "OpenFire",
    "sequence": 100,
    "init_xml" : [
    ],
    "data" : [
        'security/of_group_intranet_security.xml',
        'of_base_view.xml',
        'wizard/wizard_change_active_product.xml',
        'nom_base.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
