# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
    'name': u"OpenFire / Dossier d'impression x Gestion électronique des documents",
    'version': "10.0.1.0.0",
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'summary': u"Dossier d'impression x GED",
    'description': u"""

Module OpenFire / Dossier d'impression x Gestion électronique des documents
===========================================================================

Module permettant de définir des éléments de la GED dans les dossiers d'impression.
 
""",
    'depends': [
        'of_report_file',
        'of_document',
        'of_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_report_file_views.xml',
        'views/of_document_type_views.xml',
        'views/dms_views.xml',
        'views/crm_activity_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
