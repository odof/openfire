# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / OF Stock Product Pack",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Module de lien entre stock et produits kits",
    'depends': [
        'stock_product_pack',
    ],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
