# -*- coding: utf-8 -*-
{
    'name': 'List Editor',
    'version': '1.0.0',
    'category': '',
    'author': 'D.Jane',
    'sequence': 10,
    'summary': 'Dynamic ListView',
    'description': "Dynamic List, List Editor, Custom Fields",
    'depends': ['web'],
    'data': [
        'views/header.xml',
        'views/list_editor.xml',
        'security/ir.model.access.csv'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
