# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': "OpenFire / SAV",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': 'OpenFire modules',
    'description': u"""Modification OpenFire sur le module Odoo project_issue pour la gestion des SAV
     - Ajout du rapport SAV
     - Ajout des notes client
     - Suppression des secondes dans la date SAV
     - Ajout de l'affichage de la liste des documents (devis/commande client, devis/commande fournisseur, facture client) du client
     - Ajout du code SAV avec séquence associée
     - Ajout de la hiérarchie pour la catégorie du SAV
     - Possibilité de générer un devis ou une demande de prix depuis le SAV (menu droit).
     - Affichage des emails envoyés aux fournisseurs depuis le SAV
    """,
    # Modules sale, purchase nécessaires pour historique documents
    # of_base nécessaire pour onglet historique dans vue partenaire
    'depends': ['project_issue', 'sale', 'purchase', 'of_base', 'of_planning', 'of_gesdoc'],
    'css': [
        "static/src/css/of_project_issue.css",
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/of_project_issue_security.xml',
        'report/of_project_issue_fiche_intervention.xml',
        'report/of_project_issue_rapport_intervention.xml',
        'views/of_project_issue.xml',
        'views/of_planning_intervention_template_views.xml',
        'data/of_project_issue_canal_data.xml',
        'data/of_project_issue_sequence.xml',
    ],
    'installable': True,
}
