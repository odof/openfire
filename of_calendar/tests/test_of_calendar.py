# -*- coding: utf-8 -*-

from odoo.tests import common

# @tagged('-standard', 'OpenFire', 'of_calendar')
@common.post_install(True)
class OfTestEmployees(common.TransactionCase):
    u"""Test de la validité d'un calcul d'intersection entre les horaires de travail de deux employés
    """

    def setUp(self):
        def generate_creneaux_create_data(creneaux):
            """
            :param creneaux: Créneaux sous forme de liste de tuples : [(jour, heure_deb, heure_fin), ...]
            :return: Liste de données lisibles pour création dans une champ one2many.
            """
            result = []
            for jour, heure_deb, heure_fin in creneaux:
                creneau = self.creneau_model.search([('jour_id', '=', jour.id),
                                                     ('heure_debut', '=', heure_deb),
                                                     ('heure_fin', '=', heure_fin)], limit=1)
                if not creneau:
                    creneau = self.creneau_model.create({
                        'jour_id': jour.id,
                        'heure_debut': heure_deb,
                        'heure_fin': heure_fin,
                    })
                result.append((4, creneau.id))
            return result

        super(OfTestEmployees, self).setUp()
        self.of_jours_model = self.env['of.jours']
        self.hr_employee_model = self.env['hr.employee']
        self.creneau_model = self.env['of.horaire.creneau']
        self.generate_creneaux_create_data = generate_creneaux_create_data

        # Jours de la semaine
        lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche = self.of_jours_model.search([])

        # Jours de lundi à vendredi
        jours_semaine = self.of_jours_model.search([('numero', '<', 6)])

        # Création de 2 employés
        self.emp_1 = self.hr_employee_model.create({
            'name': 'Alphonse',
            'of_est_intervenant': True,
            'of_mode_horaires': 'easy',
            'of_hor_md': 8,
            'of_hor_mf': 12,
            'of_hor_ad': 13,
            'of_hor_af': 17,
            'of_jour_ids': [(6, 0, jours_semaine.ids)],
            'of_segment_ids': [
                (0, 0, {
                    'date_deb': '1970-01-01',
                    'date_fin': False,
                    'permanent': True,
                    'creneau_ids': generate_creneaux_create_data([
                        (jour, heure_deb, heure_fin)
                        for jour in jours_semaine
                        for heure_deb, heure_fin in ((8, 12), (13, 17))
                    ])
                })
            ]
        })

        # --------Horaires de l'employé 2 :
        # -- Juin 2019 :
        # Lundi : 8h-13h 13h30-18h
        # Mardi : 8h-11h 11h30-18h
        # Merc. : 7h-8h  9h-12h
        # Jeudi : 7h-9h  11h-14h 15h-19h
        # -- Juillet 2019
        # Lundi : 12h-18h
        # Mardi : 13h-19h
        # Jeudi : 15h-19h
        # -- Août 2019
        # Lundi : 6h-8h
        # Mardi : 8h-12h
        # Merc. : 8h-18h
        # Jeudi : 7h-19h
        # --------Horaires temporaires de l'employé 2 :
        # -- du mer.12/06 au ven.14/06
        # Jeudi : 11h-15h
        # Vend. : 11h-15h
        # -- du 01/07 au 03/07
        # Lundi : 15h-18h
        # Merc. : 8h-12h
        # -- du mar.30/07 au mer.07/08
        # Lundi : 10h-15h
        # Mardi : 10h-15h
        # Jeudi : 10h-15h
        # Vend. : 10h-15h
        self.emp_2 = self.hr_employee_model.create({
            'name': 'Bertrand',
            'of_est_intervenant': True,
            'of_mode_horaires': 'advanced',
            'of_segment_ids': [
                # HORAIRES PERMANENTS
                (0, 0, {
                    'date_deb': '1970-01-01',
                    'date_fin': '2019-06-30',
                    'permanent': True,
                    'creneau_ids': generate_creneaux_create_data([
                        (lundi, 8, 13),
                        (lundi, 13.5, 18),
                        (mardi, 8, 11),
                        (mardi, 11.5, 18),
                        (mercredi, 7, 8),
                        (mercredi, 9, 12),
                        (jeudi, 7, 9),
                        (jeudi, 11, 14),
                        (jeudi, 15, 19),
                    ])
                }),
                (0, 0, {
                    'date_deb': '2019-07-01',
                    'date_fin': '2019-07-31',
                    'permanent': True,
                    'creneau_ids': generate_creneaux_create_data([
                        (lundi, 12, 18),
                        (mardi, 13, 19),
                        (jeudi, 15, 19),
                    ])
                }),
                (0, 0, {
                    'date_deb': '2019-08-01',
                    'date_fin': False,
                    'permanent': True,
                    'creneau_ids': generate_creneaux_create_data([
                        (lundi, 6, 8),
                        (mardi, 8, 12),
                        (mercredi, 8, 18),
                        (jeudi, 7, 19),
                    ])
                }),
                # HORAIRES TEMPORAIRES
                (0, 0, {
                    'date_deb': '2019-06-12',
                    'date_fin': '2019-06-14',
                    'permanent': False,
                    'creneau_ids': generate_creneaux_create_data([
                        (jeudi, 11, 15),
                        (vendredi, 11, 15),
                    ])
                }),
                (0, 0, {
                    'date_deb': '2019-07-01',
                    'date_fin': '2019-07-03',
                    'permanent': False,
                    'creneau_ids': generate_creneaux_create_data([
                        (lundi, 15, 18),
                        (mercredi, 8, 12),
                    ])
                }),
                (0, 0, {
                    'date_deb': '2019-07-30',
                    'date_fin': '2019-08-07',
                    'permanent': False,
                    'creneau_ids': generate_creneaux_create_data([
                        (lundi, 10, 15),
                        (mardi, 10, 15),
                        (jeudi, 10, 15),
                        (vendredi, 10, 15),
                    ])
                }),
            ]
        })

    def test_employees(self):
        emps = self.emp_1 | self.emp_2
        intersec = emps.get_list_horaires_intersection('2019-01-01', '2019-12-31')

        # Horaires d'intersection attendus :
        # [ ('2019-01-01', '2019-06-08', {}),
        #   ('2019-06-09', '2019-06-12', {}),
        #   ('2019-06-13', '2019-06-30', {}),
        #   ('2019-07-01', '2019-07-03', {}),
        #   ('2019-07-04', '2019-07-29', {}),
        #   ('2019-07-30', '2019-08-04', {}),
        #   ('2019-08-05', False, {}) ]

        # Vérification du nombre d'intervalles trouvés
        self.assertEqual(len(intersec), 7, "Mauvais nombre d'intervalles : %s au lieu de 7" % len(intersec))

        # Vérification de la période de validité des intervalles
        for i, (deb, fin) in enumerate((
                ('2019-01-01', '2019-06-11'),
                ('2019-06-12', '2019-06-14'),
                ('2019-06-15', '2019-06-30'),
                ('2019-07-01', '2019-07-03'),
                ('2019-07-04', '2019-07-29'),
                ('2019-07-30', '2019-08-07'),
                ('2019-08-08', '2019-12-31')
        )):
            self.assertEqual(
                intersec[i][0],
                deb,
                u"Mauvais calcul d'intersection (date de début #%i : %s au lieu de %s)" % (i + 1, intersec[i][1], deb),
            )
            self.assertEqual(
                intersec[i][1],
                fin,
                u"Mauvais calcul d'intersection (date de fin #%i : %s au lieu de %s)" % (i + 1, intersec[i][1], fin),
            )

        # Vérification des horaires des intervalles
        self.assertEqual(
            intersec[0],
            (
                '2019-01-01', '2019-06-11',
                {
                    1: [(8.0, 12.0), (13.5, 17.0)],
                    2: [(8.0, 11.0), (11.5, 12.0), (13.0, 17.0)],
                    3: [(9.0, 12.0)],
                    4: [(8.0, 9.0), (11.0, 12.0), (13.0, 14.0), (15.0, 17.0)],
                    5: [], 6: [], 7: []
                }
            ),
            "Mauvais calcul d'intersection (#1)"
        )
        self.assertEqual(
            intersec[1],
            (
                '2019-06-12', '2019-06-14',
                {
                    1: [], 2: [], 3: [],
                    4: [(11.0, 12.0), (13.0, 15.0)],
                    5: [(11.0, 12.0), (13.0, 15.0)],
                    6: [], 7: []
                }
            ),
            "Mauvais calcul d'intersection (#2)"
        )
        self.assertEqual(
            intersec[2],
            (
                '2019-06-15', '2019-06-30',
                intersec[0][2]
            ),
            "Mauvais calcul d'intersection (#3)"
        )
        self.assertEqual(
            intersec[3],
            (
                '2019-07-01', '2019-07-03',
                {
                    1: [(15.0, 17.0)],
                    2: [],
                    3: [(8.0, 12.0)],
                    4: [], 5: [], 6: [], 7: []
                }
            ),
            "Mauvais calcul d'intersection (#4)"
        )
        self.assertEqual(
            intersec[4],
            (
                '2019-07-04', '2019-07-29',
                {
                    1: [(13.0, 17.0)],
                    2: [(13.0, 17.0)],
                    3: [],
                    4: [(15.0, 17.0)],
                    5: [], 6: [], 7: []
                }
            ),
            "Mauvais calcul d'intersection (#5)"
        )
        self.assertEqual(
            intersec[5],
            (
                '2019-07-30', '2019-08-07',
                {
                    1: [(10.0, 12.0), (13.0, 15.0)],
                    2: [(10.0, 12.0), (13.0, 15.0)],
                    3: [],
                    4: [(10.0, 12.0), (13.0, 15.0)],
                    5: [(10.0, 12.0), (13.0, 15.0)],
                    6: [], 7: []
                }
            ),
            "Mauvais calcul d'intersection (#6)"
        )
        self.assertEqual(
            intersec[6],
            (
                '2019-08-08', '2019-12-31',
                {
                    1: [],
                    2: [(8.0, 12.0)],
                    3: [(8.0, 12.0), (13.0, 17.0)],
                    4: [(8.0, 12.0), (13.0, 17.0)],
                    5: [], 6: [], 7: []
                }
            ),
            "Mauvais calcul d'intersection (#7)"
        )

        self.assertEqual(
            self.emp_2.get_horaires_date('2019-06-20')[self.emp_2.id],
            [[7.0, 9.0], [11.0, 14.0], [15.0, 19.0]],
            "Mauvais calcul d'horaire sur date (#1)"
        )

        self.assertEqual(
            self.emp_2.get_horaires_date('2019-07-03')[self.emp_2.id],
            [[8.0, 12.0]],
            "Mauvais calcul d'horaire sur date (#2)"
        )

        self.assertEqual(
            self.emp_2.get_horaires_date('2019-07-04')[self.emp_2.id],
            [[15.0, 19.0]],
            "Mauvais calcul d'horaire sur date (#3)"
        )
