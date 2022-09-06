# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Articles Téléphonie - Internet",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'website': u"http://www.openfire.fr",
    'category': u"Gestion des articles Téléphonie",
    'description': u"""
Module OpenFire pour la gestion des articles Téléphonie
=======================================================

""",
    'depends': [
        'of_contract_custom',
        'of_parc_installe',
    ],
    'data': [
        'views/of_contract_views.xml',
        'views/of_product_views.xml',
        'views/of_parc_installe_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
