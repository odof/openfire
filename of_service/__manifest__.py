# -*- encoding: utf-8 -*-

{
    'name': "OpenFire / Services",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Generic Modules",
    'description': """Module OpenFire de gestion des services.""",
    'depends': [
        'of_planning',
        'of_map_view',
        'of_utils',
        'sales_team',  # <- bouton 'prévoir intervention' dans les commandes client
        'date_range',
        #'of_base_location', < par of_planning
    ],
    'init_xml': [],
    'demo_xml': [],
    'data': [
        'security/ir.model.access.csv',
        'views/of_service_view.xml',
        'data/of_service_data.xml',
    ],
    'installable': True,
}
