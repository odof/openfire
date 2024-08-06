# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / OF sale advance payment",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Personnalisation des module de OCA ",
    'depends': [
        'sale_advance_payment',
    ],
    'data': [
        'wizard/sale_advance_payment_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
