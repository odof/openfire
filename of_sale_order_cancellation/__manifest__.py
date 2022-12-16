# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': u"OpenFire / Annulation des commandes de vente",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'license': '',
    'summary': u"Annulation commerciale des commandes de vente",
    'description': u"""
Module OpenFire / Annulation des commandes de vente
===================================================

Fonctionnalités
---------------
- Annulation commerciale : ajout de la possibilité d'annuler une commande de vente validée en créant une commande inverse
""",
    'depends': [
        'of_sale',
        'of_crm',
    ],
    'data': [
        'views/sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
