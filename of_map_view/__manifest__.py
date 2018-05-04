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
    'name' : "OpenFire - Map View",
    'version' : "10.0.1.0.0",
    'license': 'AGPL-3',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module OpenFire",
    'complexity': "",
    #'sequence': "",
    'summary': u"""  Map views """,
    'description': u"""
Module OpenFire - Nom du module
===============================
Creates a new type of view : "map".
        

Fonctionnalités
----------------
- Contains a built-in implementation for res.partner.


""",
    'depends' : [
        'web',
	'of_geolocalize',
    ],
    'external_dependancies': {
        #'python': ['pypackage1', 'pypackage2'],
    },
    'data' : [
        'data/ir_config_parameter_data.xml',
        'views/of_map_templates.xml',
        'views/of_partner_views.xml',
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
