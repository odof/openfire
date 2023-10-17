# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Questionnaires",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'license': 'LGPL-3',
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Survey customisation for Leads/Opportunities and Interventions",
    'website': 'https://www.openfire.fr',
    'depends': [
        'survey',
        'crm',
    ],
    'data': [
        'views/of_survey_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
