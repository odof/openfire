# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / OF Sale Advance Payment",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Personnalisation des modules de OCA ",
    'depends': [
        'sale_advance_payment',
        'of_sale',
        'of_account_payment',
    ],
    'data': [
        'views/sale_order_views.xml',
        'wizards/sale_advance_payment_wizard_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
