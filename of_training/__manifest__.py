# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Formations",
    'author': u"OpenFire",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'category': u"OpenFire",
    'summary': u"Outil Formation Qualiopi",
    'description': u"""
OpenFire - Training
===================
Adds a new value on product.template, the boolean is_training

Creates a new models : "of.training.modalities", "of.training.program", "of.training.equipment", "of.training.session"

Creates an entire new menu : "Training"
    """,
    'website': u"www.openfire.fr",
    'depends': [
        "product",
        "of_sale",
    ],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/of_training_views.xml',
        'views/product_views.xml',
        'views/partner_views.xml',
        'views/order_views.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
