# -*- coding: utf-8 -*-
{
    'name' : "OpenFire / Comptabilité",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'license': '',
    'website' : "www.openfire.fr",
    'category' : "Generic Modules/Accounting",
    'description': u"""
Module de comptabilité OpenFire.
======================================

- Ajout de la rubrique 'Rapports' dans les paramètres de configuration
- Factures :

  - Afficher le boutton "Envoyer par email" dans tous les cas sauf pour les factures annulées et brouillon
  - Afficher la date d'échéance dans la vue facture sans être en mode développeur
  - Permettre de modifier la date d'échéance manuellement (option dans les paramètres de configuration comptabilité : suivant les conditions de règlement/modification manuelle possible)
  - Permettre d'afficher et de rechercher des étiquettes client dans les factures
  - Ajout d'un champ 'Exporté' pour savoir ce qui a été exporté
  - Modifie le libellé des écritures comptables (Factures : client + n° facture, Paiement : client + n° facture/n° commande)
""",
    'depends' : [
        'account',
        'of_base',
    ],
    'demo_xml' : [],
    'data': [
        'views/of_account_view.xml',
        'wizards/wizard_edit_export_view.xml'
    ],
    'installable': True,
}
