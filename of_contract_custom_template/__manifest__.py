# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Modèles de contrats",
    'version': '10.0.1.0.0',
    'category': 'OpenFire',
    'author': "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Ajout des modèles de contrats OpenFire",
    'description': u"""
Modèles de contrats OpenFire
=================
Création de nouveaux modèles:
 - Contrat
 - Ligne de contrat
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_contract_custom',
        'of_questionnaire_quote_template',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_contract_template_views.xml',
        'views/of_contract_template_line_views.xml',
        'views/of_contract_template_product_views.xml',
        'views/of_contract_custom_views.xml',
        'views/of_sale_order_views.xml',
        'views/of_sale_quote_template_views.xml',
        'hooks/post_hooks.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
