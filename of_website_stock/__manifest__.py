# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Stock sur site internet",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Module OpenFire pour les stocks du site internet
================================================

""",
    'website': "www.openfire.fr",
    'depends': [
        'website',
        'of_website_sale',
        'sale_order_dates',
    ],
    'data': [
        'data/mail_template.xml',
        'data/ir_cron.xml',
        'views/website_config_views.xml',
        'views/stock_notify_views.xml',
        'templates/assets.xml',
        'templates/templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
