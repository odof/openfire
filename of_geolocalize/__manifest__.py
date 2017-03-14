# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'OpenFire Geolocation Module',
    'author':'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Company and Partners Geolocation',
    'description': """
        Allows to geolocalize partners and companies
    """,
    'website': 'openfire.fr',
    'depends': ['base'],
    'data': [
        'views/of_company_views.xml',
        'views/of_partner_views.xml'
    ],
    'installable': True,
    'auto_install': False,
}
