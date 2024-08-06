# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Openfire / Paiement d'avance de vente",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Module d'extension pour les paiements d'avance sur les ventes",
    'depends': [
        'of_sale',
        'sale_advance_payment',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
