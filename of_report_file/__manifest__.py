# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name': u"OpenFire / Dossier d'impression",
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Dossier de rapports",
    'description': u"""

Module OpenFire / Dossier d'impression
======================================

Module permettant de définir des dossiers d'impression : ensemble de rapports et de documents joints formant un dossier PDF.
 
""",
    'depends': [
        'of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_report_file_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
