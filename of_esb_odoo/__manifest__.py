# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / ESB Odoo",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "OpenFire Entreprise Service Bus - Connecteur Odoo",
    'depends': [
        'of_esb',
    ],
    "external_dependencies": {"python": ["odoorpc"]},
    'data': [
        'security/ir.model.access.csv',
        'views/of_esb_connection_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
