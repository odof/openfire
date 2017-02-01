# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Module gestion de prêt d'appareil",
    'version' : "1.1",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "OpenFire",
    'description': """
Module gestion de prêt d'appareil
""",
    'depends' : [
        'project_issue',
        'of_sav_but'
    ],
    'data' : [
        'views/of_pret_appareil_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': False,
    'active': False,
}

