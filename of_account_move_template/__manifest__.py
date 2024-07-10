# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Écritures récurrentes",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Module d'extension de account_move_template",
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_base_comment_template',
        'account_move_template',
    ],
    'data': [
        'views/account_move_template_views.xml',
        'wizards/account_move_template_run_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
