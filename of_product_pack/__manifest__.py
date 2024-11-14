# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Kits produits",
    'version': '16.0.1.2.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': 'https://www.openfire.fr',
    'category': 'OpenFire',
    'summary': "Module d'extension du module OCA product_pack",
    'depends': [
        'product_pack',
        'of_product_brand',
    ],
    'data': [
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
