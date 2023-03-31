# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
from odoo.tests.common import at_install, post_install, TransactionCase


@at_install(False)
@post_install(True)
class OFTestUsersTransactionCase(TransactionCase):
    """
    Made to create users when there is a need to test different access rights
    Call setUpXXX inside the setUp of the children class to be able to do operations as the user
    """

    def get_setUp_user_defaults(self, login=u"Tests"):
        """ Valeurs par défaut pour un utilsateur """
        res_users_obj = self.env['res.users']
        res_company_obj = self.env['res.company']
        res_groups_obj = self.env['res.groups']
        companies = res_company_obj.search([])
        vals = {
            'active': True,
            'company_id': companies[0].id,
            'company_ids': [(4, company.id) for company in companies],
            'lang': 'fr_FR',
            'login': login,
            'name': login,
            'notify_email': 'always',
            'of_user_type': 'web',
            'tz': 'Europe/Paris',
        }
        default_group_ids = res_users_obj.default_get(['groups_id'])['groups_id']
        group_ids = []
        # Paramètres technique, on récupère les droits de cette catégorie uniquement
        # les autres doivent être choisis dans le setUp approprié
        hidden = self.env.ref('base.module_category_hidden')
        for six, zero, ids in default_group_ids:
            for id in ids:
                group = res_groups_obj.browse(id)
                if group.category_id.id == hidden.id:
                    group_ids.append((4, group.id))
        vals['groups_id'] = group_ids
        return vals

    def model_obj_as_user(self, model_name, user_id):
        """ Permet de renvoyé un objet et qu'il soit utilisé comme si nous étions connecté en tant que user_id """
        return self.env[model_name].sudo(user=user_id)

    def setUpGerant(self):
        """ Modèle de droit pour un gérant """
        res_users_obj = self.env['res.users']
        vals = self.get_setUp_user_defaults(login=u"Christian")
        groups = [
            self.env.ref('muk_dms.group_dms_admin'),  # Documents / Administrator
            self.env.ref('sales_team.group_sale_manager'),  # Ventes / Gestionnaire
            self.env.ref('project.group_project_manager'),  # Projet / Gestionnaire
            self.env.ref('stock.group_stock_manager'),  # Stock / Gestionnaire
            self.env.ref('account.group_account_manager'),  # Comptabilité & finance / Conseiller
            self.env.ref('purchase.group_purchase_manager'),  # Achats / Gestionnaire
            self.env.ref('hr.group_hr_manager'),  # Employés / Gestionnaire
            self.env.ref('of_analyse_chantier.of_group_analyse_chantier_manager'),  # OF Analyse chantier / Responsable
            self.env.ref('of_sale.of_group_sale_marge_manager'),  # OF Marge / Responsable
            self.env.ref('of_planning.group_planning_intervention_manager'),  # OF Interventions / Responsable
            self.env.ref('base.group_system')  #  Administration / Configuration
        ]
        for group in groups:
            vals['groups_id'].append((4, group.id))
        self.gerant = res_users_obj.create(vals)

    def setUpGestionnaire(self):
        """ Modèle de droit pour gestionnaire """
        res_users_obj = self.env['res.users']
        vals = self.get_setUp_user_defaults(login=u"Voltaire")
        groups = [
            self.env.ref('muk_dms.group_dms_manager'),  # Documents / Manager
            self.env.ref('sales_team.group_sale_manager'),  # Ventes / Gestionnaire
            self.env.ref('project.group_project_manager'),  # Projet / Gestionnaire
            self.env.ref('stock.group_stock_manager'),  # Stock / Gestionnaire
            self.env.ref('account.group_account_user'),  # Comptabilité & finance / Comptable
            self.env.ref('purchase.group_purchase_manager'),  # Achats / Gestionnaire
            self.env.ref('hr.group_hr_manager'),  # Employés / Gestionnaire
            self.env.ref('of_analyse_chantier.of_group_analyse_chantier_manager'),  # OF Analyse chantier / Responsable
            self.env.ref('of_sale.of_group_sale_marge_manager'),  # OF Marge / Responsable
            self.env.ref('of_planning.group_planning_intervention_manager'),  # OF Interventions / Responsable
            self.env.ref('base.group_erp_manager')  #  Administration / Droits d'accès
        ]
        for group in groups:
            vals['groups_id'].append((4, group.id))
        self.gestionnaire = res_users_obj.create(vals)

    def setUpResponsable(self):
        """ Modèle de droit pour un responsable """
        res_users_obj = self.env['res.users']
        vals = self.get_setUp_user_defaults(login=u"Caïn")
        groups = [
            self.env.ref('muk_dms.group_dms_manager'),  # Documents / Manager
            self.env.ref('of_access_control.of_group_sale_responsible'),  # Ventes / Responsable
            self.env.ref('of_access_control.of_group_project_responsible'),  # Projet / Responsable
            self.env.ref('of_access_control.of_group_stock_responsible'),  # Stock / Responsable
            self.env.ref('account.group_account_user'),  # Comptabilité & finance / Comptable
            self.env.ref('purchase.group_hr_user'),  # Achats / Gestionnaire
            self.env.ref('hr.group_hr_manager'),  # Employés / Fonctionnaire
            self.env.ref('of_analyse_chantier.of_group_analyse_chantier_manager'),  # OF Analyse chantier / Responsable
            self.env.ref('of_sale.of_group_sale_marge_manager'),  # OF Marge / Responsable
            self.env.ref('of_planning.group_planning_intervention_manager'),  # OF Interventions / Responsable
            self.env.ref('of_access_control.of_group_erp_user')  #  Administration / Utilisateurs
        ]
        for group in groups:
            vals['groups_id'].append((4, group.id))
        self.responsable = res_users_obj.create(vals)

    def setUpAssistant(self):
        """ Modèle de droit pour un assistant """
        res_users_obj = self.env['res.users']
        vals = self.get_setUp_user_defaults(login=u"Chat GPT-3")
        groups = [
            self.env.ref('muk_dms.group_dms_user'),  # Documents / User
            self.env.ref('sales_team.group_sale_salesman_all_leads'),  # Ventes / Utilisateur: tous les documents
            self.env.ref('project.group_project_user'),  # Projet / Utilisateur
            self.env.ref('stock.group_stock_user'),  # Stock / Utilisateur
            self.env.ref('account.group_account_invoice'),  # Comptabilité & finance / Facturation
            self.env.ref('purchase.group_purchase_user'),  # Achats / Utilisateur
            self.env.ref('base.group_user'),  # Employés / Employé
            self.env.ref('of_analyse_chantier.of_group_analyse_chantier_user'),  # OF Analyse chantier / Utilisateur
            self.env.ref('of_sale.of_group_sale_marge_manager'),  # OF Marge / Responsable
            self.env.ref('of_planning.group_planning_intervention_manager'),  # OF Interventions / Responsable
        ]
        for group in groups:
            vals['groups_id'].append((4, group.id))
        self.assistant = res_users_obj.create(vals)

    def setUpVendeur(self):
        """ Modèle de droit pour un vendeur """
        res_users_obj = self.env['res.users']
        vals = self.get_setUp_user_defaults(login=u"Salesman")
        groups = [
            self.env.ref('muk_dms.group_dms_user'),  # Documents / User
            self.env.ref('sales_team.group_sale_salesman'),  # Ventes / Utilisateur: mes documents seulement
            self.env.ref('project.group_project_user'),  # Projet / Utilisateur
            self.env.ref('stock.group_stock_user'),  # Stock / Utilisateur
            self.env.ref('account.group_account_invoice'),  # Comptabilité & finance / Facturation
            self.env.ref('purchase.group_purchase_user'),  # Achats / Utilisateur
            self.env.ref('base.group_user'),  # Employés / Employé
            self.env.ref('of_analyse_chantier.of_group_analyse_chantier_user'),  # OF Analyse chantier / Utilisateur
        ]
        for group in groups:
            vals['groups_id'].append((4, group.id))
        self.vendeur = res_users_obj.create(vals)

    def setUpIntervenant(self):
        """ Modèle de droit pour un intervenant """
        res_users_obj = self.env['res.users']
        vals = self.get_setUp_user_defaults(login=u"Bertrand")
        groups = [
            self.env.ref('muk_dms.group_dms_manager'),  # Documents / Manager
            self.env.ref('sales_team.group_sale_manager'),  # Ventes / Gestionnaire
            self.env.ref('project.group_project_manager'),  # Projet / Gestionnaire
            self.env.ref('stock.group_stock_manager'),  # Stock / Gestionnaire
            self.env.ref('account.group_account_user'),  # Comptabilité & finance / Comptable
            self.env.ref('purchase.group_purchase_manager'),  # Achats / Gestionnaire
            self.env.ref('hr.group_hr_manager'),  # Employés / Gestionnaire
            self.env.ref('of_analyse_chantier.of_group_analyse_chantier_manager'),  # OF Analyse chantier / Responsable
            self.env.ref('of_sale.of_group_sale_marge_manager'),  # OF Marge / Responsable
            self.env.ref('of_planning.group_planning_intervention_manager'),  # OF Interventions / Responsable
            self.env.ref('base.group_erp_manager')  #  Administration / Droits d'accès
        ]
        for group in groups:
            vals['groups_id'].append((4, group.id))
        self.intervenant = res_users_obj.create(vals)

    def setUpPortail(self):
        """ Modèle de droit pour un utilisateur portail """
        res_users_obj = self.env['res.users']
        vals = self.get_setUp_user_defaults(login=u"Weird al")
        groups = [
            self.env.ref('base.group_portal'),  # Autres droits supplémentaires / portail
        ]
        for group in groups:
            vals['groups_id'].append((4, group.id))
        self.portail = res_users_obj.create(vals)

