# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Modèle de devis",
    'version': '16.0.1.1.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    "summary": "Extension du module standard sale_management",
    'website': 'https://www.openfire.fr',
    'depends': [
        'sale_management',
        'of_sale_stock',  # of_sale_stock > of_sale > of_account > of_product_brand
        'of_custom_document_sale',
    ],
    'data': [
        'views/sale_order_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_hook',
}
