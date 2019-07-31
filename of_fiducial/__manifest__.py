# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Export comptable vers logiciels Fiducial (Winfic et Winsis)",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "Accounting",
    'description': """
    - Export comptable vers logiciels Fiducial (Winfic et Winsis)
""",
    'depends' : [
        'account',
    ],
    'init_xml' : [
    ],
    'data' : [
        'wizards/wizard_of_fiducial_view.xml',
    ],
    'installable': True,
}
