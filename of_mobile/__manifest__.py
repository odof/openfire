# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Mobile",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Module permettant l'utilisation de l'application mobile",
    'depends': [
        'of_equipment',
        'of_survey',
        'of_service',
        'graphql_base',
        'of_graphql',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'data/of_planning_intervention_template.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
        'views/of_service_request_views.xml',
        'views/of_product_brand_views.xml',
        'views/of_planning_task_views.xml',
        'views/of_planning_intervention_template_views.xml',
    ],
    'external_dependencies': {
        'python': [
            'graphene',
        ]
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
