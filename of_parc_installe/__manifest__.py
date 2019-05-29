# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Module Parc installé",
    'version' : "1.1",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "OpenFire",
    'description': """
Module Parc installé : gestion des produits installés avec no de série.
""",
    'depends' : [
        'product',
        'of_project_issue',
        'of_map_view',
    ],
    'data' : [
        'security/ir.model.access.csv',
        'views/of_parc_installe_view.xml',
    ],
    'installable': True,
}
