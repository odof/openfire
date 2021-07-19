# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
{
    "name": "OpenFire / Logistics",
    "version": "10.0.1.0.0",
    "author": 'OpenFire SAS',
    "category": "OpenFire modules",
    "website": "openfire.fr",
    "description": u"""
OpenFire - Logistics :
======================
Adds a new value on product.template, the number of pallets.

Logistic rates
--------------
 - Define a carrier and the rates of said carrier for a specific department
 - Allows the use of a flat rate, rate/10kg or rate/100kg

Logistic constraints
--------------------
 - Define constraints for carriers
 - Constraints can be set on total maximum weight or nbr. of pallets

Stock pickings
--------------
 - Only available for outgoing pickings
 - New page in notebook 'Logistics' that allows the user to know the prices for each carrier
 - Every rate that was defined in the logistic rates may appear if the delivery address is in the same department.
 - If a carrier constraint is violated, the carrier is displayed with the name of the violated constraint but not the rate.
""",
    'depends': [
        'l10n_fr_department',
        'stock',
        'of_base',
        ],
    'data': [
        'views/of_logistic_views.xml',
        'views/product_views.xml',
        'views/stock_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    }
