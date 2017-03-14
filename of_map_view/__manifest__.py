# -*- coding: utf-8 -*-

{
    'name': 'OpenFire Map View',
    'author':'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Map View',
    'description': """
        creates a new type of view : "map".
        contains a built-in implementation for res.partner.
    """,
    'website': 'openfire.fr',
    'depends': ['web','of_geolocalize'],
    'data': [
        'data/ir_config_parameter_data.xml',
        'views/of_map_templates.xml',
        'views/of_partner_views.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': False,
}
