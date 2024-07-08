# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Profil utilisateur",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Module de gestion de profil utilisateur",
    'depends': ['base'],
    'data': [
        'views/res_users_views.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
