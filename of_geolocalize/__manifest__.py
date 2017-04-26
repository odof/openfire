# -*- coding: utf-8 -*-

{
    'name': 'OpenFire Geolocation',
    'author':'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Company and Partners Geolocation',
    'description': """
        Allows to geolocalize partners and companies, through geocoding (converting an address into GPS coordinates) or manually.
        Requires a geocoding server up and running.
    """,
    'website': 'openfire.fr',
    'depends': [
        'base',
        'sales_team',
    ],
    'data': [
        'wizard/of_geocode_partners_popup_view.xml',
        'views/of_company_views.xml',
        'views/of_partner_views.xml',
        'data/ir_config_parameter_data.xml',
    ],
    'installable': True,
    'auto_install': False,
}
