# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Paiments",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Personnalisation des paiements",
    'description': "",
    'depends': [
        'account_payment',
        'of_account',
        'sale_advance_payment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/of_payment_tags.xml',
        'views/account_payment_views.xml',
        'views/of_payment_mode_views.xml',
        'views/of_payment_tags_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
