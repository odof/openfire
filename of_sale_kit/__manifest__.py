# -*- coding: utf-8 -*-

{
    'name': 'OpenFire Kits',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Kits',
    'description': """
        Module de Kits openfire: \n
        \t- Création de kits à partir des nomenclatures du module mrp
        \t- Ajout des champs 'is_kit' et 'pricing' dans les produits, lignes de commandes, de factures et composants
        \t- Ajout des kits dans les Devis, Bons de commandes, et Factures clients
        \t- Possibilité de création de kits à la volée dans les Devis, Bons de commandes et Factures clients
        \t- Approvisionnement des composants sur confirmation de commande
        \t- Conversion de Bons de commandes en Factures
        \t- 3 modes d'affichage des kits dans les rapports PDF: masqué, restreint et étendu
        \t- Prix d'achat des kits en fonction de leurs composants et marges dans les Devis
    """,
    'website': 'openfire.fr',
    'depends': [
        'sale_stock',
        'mrp',
        'of_product',
        'sale_margin',
        'of_utils',
        'of_sale',
    ],
    'data': [
        'views/of_product_views.xml',
        'views/of_sale_views.xml',
        'views/of_account_views.xml',
        'report/of_sale_report_templates.xml',
        'report/of_account_report_templates.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
