# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / OpenImport",
    "version": '16.0.0.0.0',
    "license": 'AGPL-3',
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    'summary': "Module d'import de données pour OpenFire",
    "depends": [
        'of_product_brand',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/of_import_update_product_brand_products.xml',
        'views/of_import_view.xml',
        'views/of_product_brand_view.xml',
        'views/product_template_view.xml',
        'views/of_import_message.xml',
    ],
    'external_dependencies': {
        'python': ['chardet', 'xlrd', 'openpyxl'],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
