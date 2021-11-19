# -*- coding: utf-8 -*-
{
    'name': 'OpenFire / Website Mass mailing',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Summary',
    'description': u"""
OpenFire / Website Mass Mailing
===============================
""",
    'website': 'openfire.fr',
    'depends': ['website_mass_mailing'],
    'data': [
        'views/unsubscribe_templates.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': False,
}
