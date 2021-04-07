# -*- coding: utf-8 -*-

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
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module OpenFlam",
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
    ],
    'data': [
        'wizards/of_sale_order_closure_wizard_views.xml',
        'wizards/of_sale_order_confirmation_views.xml',
        'views/sale_views.xml',
        'reports/report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
