# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Information étendue sur les factures payées",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Personnalisation du module OCA Account Invoice Report Payment Extended Info",
    'depends': [
        'account_invoice_report_payment_info',
        'of_account_payment',
    ],
    'data': [
        'data/data.xml',
        'views/account_payment_method_line_views.xml',
        'reports/report_account_move.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
