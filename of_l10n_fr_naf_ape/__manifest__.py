# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Code APE et Catégorie NAF",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "AGPL-3",
    'category': "OpenFire",
    'description': u"""
Code APE et Catégorie NAF
=========================

Ajout d'un champ Code APE sur les partenaires.

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_sale',
    ],
    'data': [
        'data/of.naf.csv',
        'security/ir.model.access.csv',
        'views/of_naf_views.xml',
        'views/res_partner_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
