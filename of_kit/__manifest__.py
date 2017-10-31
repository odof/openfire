# -*- coding: utf-8 -*-

{
    'name': 'OpenFire New Kits',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Kits',
    'description': """
        Module de Kits openfire: \n
        \t- Création de kits directement dans les Articles
        \t- Ajout des champs 'is_kit' et 'pricing' dans les produits, lignes de commandes, de factures et composants
        \t- Ajout des kits dans les Devis, Bons de commandes, et Factures clients
        \t- Possibilité de création de kits à la volée dans les Devis, Bons de commandes et Factures clients
        \t- Approvisionnement des composants sur confirmation de commande
        \t- Conversion de Bons de commandes en Factures
        \t- 3 modes d'affichage des kits dans les rapports PDF: aucun, restreint et étendu
        \t- Prix d'achat des kits en fonction de leurs composants et marges dans les Devis
    """,
    'website': 'openfire.fr',
    'depends': [
        'of_sale_stock',
        'of_product',
        'sale_margin',
        'of_web_widgets',
        'of_purchase',
        ],
    'data': [
        'views/of_kit_views.xml',
        'report/of_kit_report_templates.xml',
        'security/ir.model.access.csv',
        'data/of_kit_data.xml',
    ],
    'installable': True,
    'auto_install': False,
}
