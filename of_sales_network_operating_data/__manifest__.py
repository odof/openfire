# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Réseau Commercial - Données d'exploitation",
    'version': '10.0.1.1.0',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'summary': u"Réseau Commercial - Données d'exploitation",
    'license': 'AGPL-3',
    'description': u"""
Module OpenFire permettant de récupérer les données d'exploitatioon des membres d'un réseau
===========================================================================================
""",
    'website': u"www.openfire.fr",
    'depends': [
        'of_sales_network',
    ],
    'data': [
        'data/cron.xml',
        'security/ir.model.access.csv',
        'views/of_operating_data_views.xml',
        'views/of_sale_network_config_settings_views.xml',
        'views/templates.xml',
        'reports/of_operating_data_report_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
}
