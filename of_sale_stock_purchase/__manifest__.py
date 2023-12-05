# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Sale Stock Purchase",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Prise en compte de la méthode de coût des produits dans le calcul de la marge de vente",
    'depends': [
        'of_sale_margin',
        'of_purchase_stock',  # of_purchase_stock > of_stock_account > of_account
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}
