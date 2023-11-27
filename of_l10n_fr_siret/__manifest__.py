# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Option SIREN/NIC",
    'version': '10.0.2.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'website': u"http://www.openfire.fr",
    'category': u"OpenFire",
    'description': u"""
OpenFire / Option SIREN/NIC
===========================

Fonctionnalités :
------------------

* Ajout d'une option dans la configuration générale pour rendre le SIREN obligatoire sur les partenaires de type société
* Modification de la vue formulaire de configuration des paramètres d'impression des devis pour ajouter l'option SIRET :
    - Afficher le SIRET dans l'adresse du client;
    - Afficher le SIRET dans la pastille client.
* Modification de la vue formulaire de configuration des paramètres d'impression des factures pour ajouter l'option SIRET :
    - Afficher dans l'encart d'adresse principal;
    - Afficher dans une pastille d'informations complémentaires;
    - Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires.
* Ajustement des rapports de devis et factures pour prendre en compte les options SIRET.
""",
    'depends': [
        'l10n_fr_siret',
        'of_sale',
        'of_account_invoice_report',
    ],
    'init_xml': [],
    'demo_xml': [],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/account_config_settings_views.xml',
        'wizards/sale_set_printing_params_view.xml',
        'report/of_sale_report_template.xml',
        'report/of_account_invoice_template.xml'
    ],
    'installable': True,
}
