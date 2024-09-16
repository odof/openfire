# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / SMS Account",
    'version': "16.0.1.0.0",
    'license': 'LGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Module de SMS OpenFire pour la comptabilité",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_sms',
        'of_account',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
}
