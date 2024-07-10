# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Gestion prix & échéancier de paiement",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'summary': "Link module between Price management and Payment schedule",
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_sale_price_management',
        'of_sale_payment_schedule'
    ],
    'data': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
