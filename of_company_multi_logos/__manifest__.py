# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OpenFire Multi logos',
    'author':'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Multi logos',
    'description': """
        Allow a company to have several logos as secondary logos.
        These logos are displayed in a tab named "logo" in the company form.
    """,
    'website': 'openfire.fr',
    'depends': [],
    'data': [
        'views/of_company_multi_logos_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
