# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Ventes Kanban",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "sequence": 15,
    "website": "https://www.openfire.fr",
    "depends": [
        "of_sale_crm",
    ],
    "data": [
        "data/of_sale_order_kanban_stage.xml",
        "security/ir.model.access.csv",
        "views/of_sale_order_kanban_stage_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "of_sale_kanban/static/src/scss/of_sale_kanban.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
