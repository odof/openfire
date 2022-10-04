# -*- coding: utf-8 -*-

from odoo.tests import common
from odoo.addons.of_calendar.tests.test_of_calendar import OfTestEmployees


# @tagged('-standard', 'OpenFire', 'of_calendar')
@common.post_install(True)
class OfTestPlannings(OfTestEmployees):
    u"""Test de la validité d'un calcul de créneaux disponibles
    """

    def setUp(self):
        super(OfTestPlannings, self).setUp()
        self.creneau_model = self.env['of.horaire.creneau']
        self.intervention_model = self.env['of.planning.intervention']
        self.tache_1 = self.env['of.planning.tache'].create({
            'name': 'Tâche de test 1',
        })

    def test_creneaux(self):

        # Tests sur la semaine du lundi 04/11/2019 au vendredi 08/11/2019
        # Durant cette semaine, les horaires sont :
        # emp_1 : 8-12 13-17
        # emp_2 :
        # Juin 2019
        # Lundi : 8h-13h 13h30-18h
        # Mardi : 8h-11h 11h30-18h
        # Merc. : 7h-8h  9h-12h
        # Jeudi : 7h-9h  11h-14h 15h-19h
        # Vend. : ne travaille pas

        # Novembre 2019
        # Lundi : 6h-8h
        # Mardi : 8h-12h
        # Merc. : 8h-18h
        # Jeudi : 7h-19h
        # Vend. : ne travaille pas

        interventions_juin = self.intervention_model.browse()
        emp_ids = [self.emp_1.id, self.emp_2.id]
        for jour in xrange(3, 8):
            interventions_juin |= self.intervention_model.create({
                # Interventions du lundi 03/06 au vendredi 07/06/2019, de 12h à 15h
                # En juin on est en UTC+2
                'name': '2019-06-%02i' % jour,
                'date': '2019-06-%02i 10:00:00' % jour,
                'date_deadline_forcee': '2019-06-%02i 13:00:00' % jour,
                'duree': 3,
                'forcer_dates': True,
                'tache_id': self.tache_1.id,
                'employee_ids': [(6, 0, emp_ids)],
            })

        interventions_novembre = self.intervention_model.browse()
        for jour in xrange(4, 9):
            interventions_novembre |= self.intervention_model.create({
                # Interventions du lundi 04/11 au vendredi 08/11/2019, de 10h à 13h
                # En novembre on est en UTC+1
                'name': '2019-11-%02i' % jour,
                'date': '2019-11-%02i 09:00:00' % jour,
                'date_deadline_forcee': '2019-11-%02i 12:00:00' % jour,
                'duree': 2,
                'forcer_dates': True,
                'tache_id': self.tache_1.id,
                'employee_ids': [(6, 0, emp_ids)],
            })

        # Informations sur les horaires du lundi 04/11 au vendredi 08/11/2019
        intervention_obj = self.intervention_model.with_context(emp_info_force_min_date='1970-01-01')
        infos_juin = intervention_obj.get_emp_horaires_info(emp_ids, '2019-06-03 02:00:00', '2019-06-07 23:00:00')
        infos_novembre = intervention_obj.get_emp_horaires_info(emp_ids, '2019-11-04 02:00:00', '2019-11-08 23:00:00')

        # Test des créneaux de l'employé 1 :
        creneaux_1_juin = infos_juin[self.emp_1.id]['creneaux_dispo'][0]
        creneaux_1_novembre = infos_novembre[self.emp_1.id]['creneaux_dispo'][0]

        self.assertEqual(len(creneaux_1_juin), 2,
                         u"Mauvais nombre de créneaux #1 : %s au lieu de 2" % len(creneaux_1_juin))
        self.assertEqual(len(creneaux_1_novembre), 2,
                         u"Mauvais nombre de créneaux #2 : %s au lieu de 2" % len(creneaux_1_novembre))

        horaires_attendus = [
            # Employé 1 - juin
            [(8, 12, 4), (15, 17, 2)],
            # Employé 1 - novembre
            [(8, 10, 2), (13, 17, 4)],
            # Employé 2 - juin
            [(8, 12, 4), (15, 18, 3)],
            [(8, 12, 3.5), (15, 18, 3)],
            [(7, 12, 4)],
            [(7, 12, 3), (15, 19, 4)],
            [],
            # Employé 2 - novembre
            [(6, 8, 2)],
            [(8, 10, 2)],
            [(8, 10, 2), (13, 18, 5)],
            [(7, 10, 3), (13, 19, 6)],
            [],
        ]

        for i, creneaux in enumerate(
            [creneaux_1_juin, creneaux_1_novembre] +
            infos_juin[self.emp_2.id]['creneaux_dispo'][:5] +
            infos_novembre[self.emp_2.id]['creneaux_dispo'][:5]
        ):
            horaires = [(c['heure_debut'], c['heure_fin'], c['duree']) for c in creneaux]
            self.assertEqual(
                horaires,
                horaires_attendus[i],
                "Mauvais calcul d'horaires, i = %s" % i)
