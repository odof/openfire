# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Openfire / Matrice de vente",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Module d'extension pour les matrices de vente",
    'depends': [
        'of_sale',
        'sale_product_matrix',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
