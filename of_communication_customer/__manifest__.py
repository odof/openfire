# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Communication Customer",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Gestion de la communication",
    'description': "",
    'depends': [
        'base',
        'mail',
        'of_communication_base',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/of_communication_message_views.xml',
        'views/of_communication_menus.xml',

        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
