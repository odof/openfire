# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / SMS Sale",
    'version': "16.0.1.0.0",
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Module de SMS OpenFire pour les ventes",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_sms',
        'of_sale',
    ],
    'data': [
        'data/ir_actions_server.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
