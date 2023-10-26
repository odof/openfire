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
#    Copyright © 2004-2016 Odoo S.A. License GNU LGPL
#
##############################################################################

{
    'name': "OpenFire / Questionnaire + Modèles de devis",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "questionnaire",
    'summary': u"Ajout des modèles d'intervention dans les modèles de devis",
    'description': u"""
Module OpenFire - Questionnaire Modèle de devis
===============================================
Ce module ajoute les modèles d'interventiosn dans les modèles de devis

Fonctionnalités
---------------
 - Ajout d'un onglet "Questionnaire" dans les modèles de devis, contenant le questionnaire du modèle d'intervention lié.
 - Au moment de créer un RDV depuis une CC qui contient un modèle de devis, charge le modèle d'intervention s'il y a lieu. Ainsi que le questionnaire lié.
""",
    'depends': [
        'of_questionnaire',
        'of_sale_quote_template',
    ],
    'data': [
        'views/of_questionnaire_quote_template_views.xml',
        'views/sale_config_settings.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
