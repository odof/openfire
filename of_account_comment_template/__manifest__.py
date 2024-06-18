# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Openfire / Commentaires de comptabilité",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Module d'extension OCA pour les commentaires de comptabilité",
    'depends': [
        'of_base_comment_template',
        'account_comment_template',
    ],
    'data': [
        'views/account_move_views.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
