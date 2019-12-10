# -*- coding: utf-8 -*-

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
    'name': "OpenFire / Gestion CRM des fabricants",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module Fabricants OpenFire",
    'summary': u"Gestion CRM",
    'description': u"""
Module OpenFire pour le CRM Odoo
================================

 - Ajout des marques distribuées dans le formulaire du contact.
""",
    'depends': [
        'of_base',
        'of_product_brand',
    ],
    'data': [
        'views/ofab_crm_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
