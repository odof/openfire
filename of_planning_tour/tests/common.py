# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields

from odoo.addons.of_service.tests.common import TestOFServiceCommon

SAINT_GREGOIRE_VICTORIA_LAT_LNG = ("48.1513003", "-1.6985415")
RENNES_COULABIN_LAT_LNG = ("48.1096790", "-1.6918783")
RENNES_CHAMP_JUSTICE_LAT_LNG = ("48.1104433", "-1.7080492")
RENNES_ORMEAUX_LAT_LNG = ("48.1038349", "-1.6105979")
PACE_BRIZEUX_LAT_LNG = ("48.1467564", "-1.7725336")


class TestOFPlanningTourCommon(TestOFServiceCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.calendar_obj = cls.env["calendar.event"]
        cls.planning_tour_obj = cls.env["of.planning.tour"]
        cls.tour_appointment_wizard_obj = cls.env["of.tour.appointment.wizard"]

        cls.now_dt = fields.Datetime.now() + timedelta(days=1)
        (
            cls.now_dt_8am,
            cls.now_dt_9am,
            cls.now_dt_10am,
            cls.now_dt_11am,
            cls.now_dt_12pm,
            cls.now_dt_1pm,
            cls.now_dt_2pm,
            cls.now_dt_3pm,
            cls.now_dt_4pm,
            cls.now_dt_5pm,
            cls.now_dt_6pm,
        ) = (
            cls.now_dt.replace(hour=8, minute=0),
            cls.now_dt.replace(hour=9, minute=0),
            cls.now_dt.replace(hour=10, minute=0),
            cls.now_dt.replace(hour=11, minute=0),
            cls.now_dt.replace(hour=12, minute=0),
            cls.now_dt.replace(hour=13, minute=0),
            cls.now_dt.replace(hour=14, minute=0),
            cls.now_dt.replace(hour=15, minute=0),
            cls.now_dt.replace(hour=16, minute=0),
            cls.now_dt.replace(hour=17, minute=0),
            cls.now_dt.replace(hour=18, minute=0),
        )

        cls.partner_antoine = cls.env["res.partner"].create(
            {
                "name": "Antoine",
                "street": "3 rue Coulabin",
                "zip": "35000",
                "city": "Rennes",
                "email": "antoine@test.fr",
                "partner_latitude": RENNES_COULABIN_LAT_LNG[0],
                "partner_longitude": RENNES_COULABIN_LAT_LNG[1],
                "of_geocoding_state": "success",
            }
        )

        cls.partner_saif = cls.env["res.partner"].create(
            {
                "name": "Saïf",
                "street": "18 rue du champ de la justice",
                "zip": "35000",
                "city": "Rennes",
                "email": "saif@test.fr",
                "partner_latitude": RENNES_CHAMP_JUSTICE_LAT_LNG[0],
                "partner_longitude": RENNES_CHAMP_JUSTICE_LAT_LNG[1],
                "of_geocoding_state": "success",
            }
        )

        cls.partner_hounaida = cls.env["res.partner"].create(
            {
                "name": "Hounaida",
                "street": "13 rue des ormeaux",
                "zip": "35000",
                "city": "Rennes",
                "email": "hounaida@test.fr",
                "partner_latitude": RENNES_ORMEAUX_LAT_LNG[0],
                "partner_longitude": RENNES_ORMEAUX_LAT_LNG[1],
                "of_geocoding_state": "success",
            }
        )

        cls.partner_guillaume = cls.env["res.partner"].create(
            {
                "name": "Guillaume",
                "street": "11 avenue Brizeux",
                "zip": "35740",
                "city": "Pacé",
                "email": "guillaume@test.fr",
                "partner_latitude": PACE_BRIZEUX_LAT_LNG[0],
                "partner_longitude": PACE_BRIZEUX_LAT_LNG[1],
                "of_geocoding_state": "success",
            }
        )
