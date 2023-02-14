# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / UTM",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'utm',
    ],
    'data': [
        'views/utm_campaign_views.xml',
        'views/utm_medium_views.xml',
        'views/utm_source_views.xml',
        'views/utm_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
