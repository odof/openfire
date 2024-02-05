# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Débours avec sous-traitance",
    'author': "OpenFire",
    'version': '10.0.1.0.0',
    'category': "Generic Modules",
    'description': u"""Débours avec sous-traitance des services.
""",
    'depends': [
        'of_outlay_management',
        'of_subcontracted_service',
    ],
    'data': [
        'views/of_outlay_analysis_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
