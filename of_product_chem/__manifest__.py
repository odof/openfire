# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Articles Cheminées",
    'version': "10.0.2.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Articles Cheminées
------------------

Mise en place d'un nouvel onglet "Technique" sur la fiche article avec des champs relatifs aux normes des cheminées.
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_import',
        'of_sale_norme',
    ],
    'data': [
        'views/of_product_chem_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
