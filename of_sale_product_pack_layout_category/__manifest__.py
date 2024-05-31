# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Ventes & Kits produits pour les sections avancées",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'summary': "Module de liaisons entre la gestion de vente produits kits et les sections avancées",
    'category': 'OpenFire',
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_sale_product_pack',
        'of_sale_layout_category',
    ],
    'assets': {
        'web.assets_backend': [
            'of_sale_product_pack_layout_category/static/src/**/*',
        ],
    },
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}
