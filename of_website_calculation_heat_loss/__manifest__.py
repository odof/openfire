# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Formulaire de calcul de déperdition de chaleur",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'description': u"""
Formulaire de calcul de déperdition de chaleur pour le site web
===============================================================
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_calculation_heat_loss',
        'website_form',
        'partner_firstname',
    ],
    'category': "OpenFire",
    'data': [
        'security/ir.model.access.csv',
        'templates/assets.xml',
        'templates/heat_loss_calculation_form_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
