# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Web Widgets",
    "version": "16.0.1.0.1",
    "author": "OpenFire",
    "license": "AGPL-3",
    "category": "OpenFire",
    "sequence": 15,
    "summary": "Web Widgets for OpenFire",
    "website": "https://www.openfire.fr",
    "depends": [
        "base",
        "base_geolocalize",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "of_web_widgets/static/src/**/*",
            "of_web_widgets/static/lib/leaflet/leaflet.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
