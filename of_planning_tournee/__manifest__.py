# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS sous licence AGPL-3.0
#
#    Compatible avec Odoo 10 Community Edition
#    Copyright © 2004-2016 Odoo S.A. License GNU LGPL
#
##############################################################################

{
    'name' : "OpenFire - Planning des tournées",
    'version' : "10.0.1.0.0",
    'license': 'AGPL-3',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Generic Modules/Gestion des interventions",
    'summary': u"Planification et gestion des tournées",
    'description': u"""
Module OpenFire - Planning des tournées
=======================================
Module pour la gestion des tournées


Fonctionnalités
----------------
- Planification RDV dans Planning Intervention
- RDV pour les clients
- Recherche géolocalisée des clients (Adresse Livraison)

""",
    'depends' : [
        'of_planning',
        'of_service',
        'of_geolocalize',
        # 'of_gesdoc',
        # 'of_imports',
        'of_base_location',
        'of_map_view',
    ],
    'external_dependancies': {
        #'python': ['pypackage1', 'pypackage2'],
    },
    'data' : [
         'security/ir.model.access.csv',
        # 'wizard/add_partner_view.xml',
        'wizard/rdv_view.xml',
        'wizard/planification_view.xml',
        # 'wizard/search_partner_view.xml',
        # 'wizard/impression_view.xml',
        'views/of_planning_tournee_view.xml',
        # 'of_planning_res_report.xml',
        # 'data/of_imports_prechamp_client.xml',
    ],
    'demo': [],
    'demo_xml' : [],
    'init_xml' : [],
    'css' : [
        #'static/src/css/*.css',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'active': True,
    'installable': True,
    'application': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4: