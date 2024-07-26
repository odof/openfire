# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Kits produits / Marge de vente",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': 'https://www.openfire.fr',
    'category': 'OpenFire',
    'summary': "Module intermédiaire entre le module of_product_pack et of_sale_margin_summary",
    'depends': [
        'of_product_pack',
        'of_sale_margin',
    ],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
