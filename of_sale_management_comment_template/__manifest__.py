# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "Openfire / Commentaires sur les modèles de devis",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Module intermédiaire entre les modèles de devis et les commentaires de vente",
    'depends': [
        'of_sale_management_template',
        'of_sale_comment_template',
    ],
    'data': [
        'views/sale_order_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
