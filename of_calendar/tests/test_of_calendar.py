# -*- coding: utf-8 -*-

from odoo.tests import common

# @tagged('-standard', 'OpenFire', 'of_calendar')
@common.post_install(True)
class OfTestEmployees(common.TransactionCase):
    u"""Test de la validité d'un calcul d'intersection entre les horaires de travail de deux employés
    """

    def setUp(self):
        super(OfTestEmployees, self).setUp()
        self.of_jours_model = self.env['of.jours']
        self.hr_employee_model = self.env['hr.employee']

    def test_employees(self):
        # Jours de lundi à vendredi
        jours_semaine = self.of_jours_model.search([('numero', '<', 6)])
        # Création de 2 employés
        emp_1 = self.hr_employee_model.create({
            'name': 'Alphonse',
            'of_est_intervenant': True,
            'of_mode_horaires': 'easy',
            'of_hor_md': 8,
            'of_hor_mf': 12,
            'of_hor_ad': 13,
            'of_hor_af': 17,
            'of_jour_ids': [(6, 0, jours_semaine.ids)],
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
        # -- du mer.09/06 au ven.12/06
        # Jeudi : 11h-15h
        # Vend. : 11h-15h
        # -- du 01/07 au 03/07
        # Merc. : 15h-18h
        # Vend. : 8h-12h
        # -- du jeu.30/07 au mar.04/08
        # Jeudi : 10h-15h
        # Vend. : 10h-15h
        # Lundi : 10h-15h
        # Mardi : 10h-15h
        emp_2 = self.hr_employee_model.create({
            'name': 'Bertrand',
            'of_est_intervenant': True,
            'of_mode_horaires': 'advanced',
            # of_creneau_ids est mis avec des valeurs identiques à celles de la dernière ligne d'archives.
            'of_creneau_ids': [
                (0, 0, {'jour_id': self.env.ref('of_utils.of_jours_1').id, 'heure_debut': 6, 'heure_fin': 8}),
                (0, 0, {'jour_id': self.env.ref('of_utils.of_jours_2').id, 'heure_debut': 8, 'heure_fin': 12}),
                (0, 0, {'jour_id': self.env.ref('of_utils.of_jours_3').id, 'heure_debut': 8, 'heure_fin': 18}),
                (0, 0, {'jour_id': self.env.ref('of_utils.of_jours_4').id, 'heure_debut': 7, 'heure_fin': 19}),
            ],
            'of_archive_horaires': (
                """["2019-06-01", "2019-06-30", {"lun.": [[8.0, 13.0], [13.5, 18.0]], "mar.": [[8.0, 11.0], [11.5, 18.0]], "mer.": [[7.0, 8.0], [9.0, 12.0]], "jeu.": [[7.0, 9.0], [11.0, 14.0], [15.0, 19.0]]}]
["2019-07-01", "2019-07-31", {"lun.": [[12.0, 18.0]], "mar.": [[13.0, 19.0]], "jeu.": [[15.0, 19.0]]}]
["2019-08-01", false, {"lun.": [[6.0, 8.0]], "mar.": [[8.0, 12.0]], "mer.": [[8.0, 18.0]], "jeu.": [[7.0, 19.0]]}]"""),
            'of_archive_horaires_temp': (
                """["2019-06-09", "2019-06-12", {"jeu.": [[11.0, 15.0]], "ven.": [[11.0, 15.0]]}]
["2019-07-01", "2019-07-03", {"mer.": [[15.0, 18.0]], "ven.": [[8.0, 12.0]]}]
["2019-07-30", "2019-08-04", {"jeu.": [[10.0, 15.0]], "ven.": [[10.0, 15.0]], "lun.": [[10.0, 15.0]], "mar.": [[10.0, 15.0]]}]"""),
        })

        emps = emp_1 | emp_2
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
            ('2019-01-01', '2019-06-08'),
            ('2019-06-09', '2019-06-12'),
            ('2019-06-13', '2019-06-30'),
            ('2019-07-01', '2019-07-03'),
            ('2019-07-04', '2019-07-29'),
            ('2019-07-30', '2019-08-04'),
            ('2019-08-05', '2019-12-31')
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
                '2019-01-01', '2019-06-08',
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
                '2019-06-09', '2019-06-12',
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
                '2019-06-13', '2019-06-30',
                intersec[0][2]
            ),
            "Mauvais calcul d'intersection (#3)"
        )
        self.assertEqual(
            intersec[3],
            (
                '2019-07-01', '2019-07-03',
                {
                    1: [], 2: [],
                    3: [(15.0, 17.0)],
                    4: [],
                    5: [(8.0, 12.0)],
                    6: [], 7: []
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
                '2019-07-30', '2019-08-04',
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
                '2019-08-05', '2019-12-31',
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
