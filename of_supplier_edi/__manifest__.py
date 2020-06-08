# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / EDI Fournisseur",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module générique EDI pour les commandes d'achat
===============================================

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_base',
        'of_purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
        'views/of_supplier_edi_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
