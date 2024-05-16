# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Questionnaires intervention",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Module de liaison entre les interventions et les questionnaires",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_planning',
        'of_survey',
    ],
    'assets': {
        'web.assets_backend': [
            'of_planning_survey/static/src/scss/survey_survey_views.scss',
        ],
    },
    'data': [
        'data/of_planning_intervention_template.xml',
        'views/calendar_event_views.xml',
        'views/of_planning_intervention_template_views.xml',
        'reports/report_intervention_report.xml',
        'reports/report_intervention_sheet.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
