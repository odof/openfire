{
    'name': 'OpenFire / Custom Documents',
    'author': 'OpenFire',
    'version': '16.0.1.0.0',
    'category': 'Documents',
    'depends': ['sale'],
    'external_dependencies': {
        'python': ['pdfminer', 'pypdftk'],
    },
    'data': [
        'report/ir_actions_report_templates.xml',
        'views/ir_actions_views.xml',
        'views/of_custom_document_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
