# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name': u"OpenFire / Ventes - Workflow commande spécifique",
    'version': '10.0.2.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'website': u"www.openfire.fr",
    'category': u"Module OpenFlam",
    'summary': u"Personnalisation du worflow des commandes de vente",
    'description': u"""

Module OpenFire / Ventes - Workflow commande spécifique
=======================================================

Module ajoutant une étape intermédiaire dans le workflow des commandes de vente.
 
""",
    'depends': [
        'of_crm',
        'of_sale_payment',
        'of_followup',
        'of_access_control',
        'of_planning',
        'of_sale_order_cancellation',
        'of_retail_analysis',
        'of_sale_type',
    ],
    'data': [
        'data/of_sale_custom_workflow_data.xml',
        'security/ir.model.access.csv',
        'security/of_sale_custom_workflow_security.xml',
        'wizards/of_sale_order_closure_wizard_views.xml',
        'wizards/of_sale_order_confirmation_views.xml',
        'views/sale_views.xml',
        'reports/report_templates.xml',
        'reports/of_crm_funnel_conversion_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
