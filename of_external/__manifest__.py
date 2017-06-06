# -*- coding: utf-8 -*-

{
    'name': 'OpenFire External',
    'author':'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Default PDF header/footer rendering',
    'description': """
        
    """,
    'website': 'openfire.fr',
    'depends': ['of_company_multi_logos'],
    'data': [
        'views/of_external_layout.xml',
        'views/of_company_views.xml'
    ],
    'installable': True,
    'auto_install': False,
}
