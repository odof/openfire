# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'OpenFire / Mass mailing',
    'author': 'OpenFire',
    'version': '10.0.1.0.0',
    'licence': 'AGPL-3',
    'category': u"OpenFire",
    'summary': 'Summary',
    'description': u"""
OpenFire / Mass Mailing
=======================
""",
    'website': 'openfire.fr',
    'depends': ['mass_mailing'],
    'data': [
        'views/config_settings_views.xml',
        'views/mass_mailing_views.xml',
    ],
    'qweb': [],
    'installable': True,
    'auto_install': False,
}
