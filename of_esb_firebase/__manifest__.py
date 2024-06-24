# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / ESB Firebase",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "OpenFire Entreprise Service Bus - Firebase",
    'depends': [
        'of_esb',
    ],
    'data': [
        'data/res_partner.xml',
        'data/res_users.xml',
        'data/of_esb_security.xml',
        'data/of_esb_connection.xml',
        'data/of_esb_trigger.xml',
        'data/of_esb_service.xml',
        'data/of_esb_rule.xml',
        'views/of_esb_connection_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
