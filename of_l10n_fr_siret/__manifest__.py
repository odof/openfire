# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Option SIREN/NIC",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'website': u"http://www.openfire.fr",
    'category': u"OpenFire",
    'description': u"""
OpenFire / Option SIREN/NIC
===========================

 - Ajout d'une option dans la configuration générale pour rendre le SIREN obligatoire sur les partenaires de type société
""",
    'depends': [
        'l10n_fr_siret',
    ],
    'init_xml': [],
    'demo_xml': [],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
}
