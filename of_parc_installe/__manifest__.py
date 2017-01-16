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
    ],
    'data' : [
        'security/ir.model.access.csv',
        'of_parc_installe_view.xml',
    ],
    'installable': False,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
