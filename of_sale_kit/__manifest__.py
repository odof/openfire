# -*- coding: utf-8 -*-

{
    'name': 'OpenFire Kits',
    'author':'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Kits',
    'description': """
        Module de Kits openfire: \n
        \t- Création de kits à partir des nomenclatures du module mrp
        \t- Ajout des champs 'is_kit' et 'pricing' dans les produits, lignes de commandes et composants
        \t- Ajout des kits dans les Bons de commandes
        \t- Possibilité de création de kits à la volée dans les Bons de commandes
        \t- 2 modes d'affichage des kits dans les rapports PDF: restreint et étendu 
    """,
    'website': 'openfire.fr',
    'depends': ['sale','mrp'],
    'data': [
        'views/of_product_views.xml',
        'views/of_sale_views.xml',
        'views/of_account_views.xml',
        #'views/of_component_views.xml',
        'report/of_sale_report_templates.xml',
        'report/of_account_report_templates.xml',
    ],
    'qweb': [
        
    ],
    'installable': True,
    'auto_install': False,
}
