# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Projets CRM",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Questionnaire dans les leads",
    'depends': [
        'of_crm',
        'of_survey',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/of_survey_survey_views.xml',
        'templates/of_survey_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'of_crm_project/static/src/js/survey.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
