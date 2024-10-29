# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / module Wizville - Jotul (fournisseur)",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Implémentation de l'api Wizville spécifique Jotul (partie fournisseur)
======================================================================

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_wizville_base',
    ],
    'data': [
        'views/product_supplierinfo_views.xml',
        ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
