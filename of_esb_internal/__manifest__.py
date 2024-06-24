# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / ESB Internal",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "OpenFire Entreprise Service Bus - Connecteur Internal",
    'depends': [
        'of_esb',
    ],
    'data': [
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
