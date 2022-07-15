# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Articles Cheminées",
    'version': '10.0.3.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Articles Cheminées
==================

Mise en place d'un nouvel onglet "Technique" sur la fiche article avec des champs relatifs aux normes des cheminées.
""",
    'website': u"www.openfire.fr",
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
