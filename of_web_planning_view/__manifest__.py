# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Web Planning view",
    'version': '16.0.1.0.1',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Vue web planning",
    'depends': [
        'of_base',
        'web',
    ],
    'data': [
        'views/resource_resource_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'of_web_planning_view/static/scss/planning_variable.scss',
        ],
        'web.assets_backend': [
            'of_web_planning_view/static/src/**/*',
            'of_web_planning_view/static/scss/planning_view.scss',
            'of_web_planning_view/static/scss/planning_cell_buttons.scss',
            'of_web_planning_view/static/scss/planning_tooltips.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
