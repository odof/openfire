# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name': u"OpenFire / Info de facturation des clients",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Ajout d'informations liées à la facturation dans la fiche du partenaire.

- Smart-button des factures non soldées
- Smart-button des commandes à facturer
""",
    'depends': ['sale'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
}
