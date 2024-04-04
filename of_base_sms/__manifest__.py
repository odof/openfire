# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / SMS et OF Base",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Module de lien entre sms et of base afin gérer le conflit entre les deux modules",
    'website': "https://www.openfire.fr",
    'depends': [
        'sms',
        'of_base',
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
