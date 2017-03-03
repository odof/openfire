# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
        "name" : "OpenFire / Planning des tournées",
        "version" : "0.9",
        "author" : "OpenFire",
        "website" : "http://www.openfire.fr",
        "category" : "Generic Modules/Gestion des interventions",
        "description": """ Gestion des tournées
         - Planification RDV dans Planning Intervention
         - RDV pour les clients
         - Recherche géolocalisée des clients (Adresse Livraison)""",
        "depends" : [
                     'of_planning',
                     'of_service',
                     'of_geolocalize',
#                     'of_gesdoc',
#                     'of_imports',
                     ],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        "update_xml" : [
#            'security/ir.model.access.csv',
#            'wizard/add_partner_view.xml',
            'wizard/res_view.xml',
#            'wizard/planification_view.xml',
#            'wizard/search_partner_view.xml',
#            'wizard/impression_view.xml',
            'views/of_planning_tournee_view.xml',
#            'of_planning_res_report.xml',
#            'data/of_imports_prechamp_client.xml',
        ],
        "installable": True,
        'active': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
