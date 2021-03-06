# -*- coding: utf-8 -*-

{
    'name': 'OpenFire / Vue carte (cartographie)',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Map View',
    'description': """
        Creates a new type of view : "map".
        Contains a built-in implementation for res.partner.
    """,
    'website': 'openfire.fr',
    'depends': ['web', 'of_geolocalize', 'contacts', 'of_web_widgets'],
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
