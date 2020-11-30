# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Point de Vente multi-sociétés",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Point de Vente multi-sociétés OpenFire
=============================================

""",
    'depends': [
        'of_point_of_sale',
        'of_base_multicompany',
    ],
    'data': [
        'security/of_pos_multicompany_security.xml',
        'views/of_pos_multicompany_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
