# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Portail du site internet / Ventes - Workflow commande spécifique",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Module OpenFire de lien entre Portail du site internet et Ventes - Workflow commande spécifique
===============================================================================================

""",
    'website': u"www.openfire.fr",
    'depends': [
        'of_website_portal',
        'of_sale_custom_workflow',
    ],
    'data': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
