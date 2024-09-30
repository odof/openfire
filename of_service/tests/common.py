# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestOFServiceCommon(TestOFPlanningCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Updates template data
        cls.template_installation.type_id = cls.env.ref("of_service.of_service_request_type_installation").id
        cls.template_sweeping.type_id = cls.env.ref("of_service.of_service_request_type_maintenance").id

        # Partner data
        cls.partner_tony = cls.env["res.partner"].create(
            {
                "name": "Tony Tagada",
                "street": "1, rue du Poêle",
                "zip": "35000",
                "city": "Rennes",
                "email": "tony.tagada@dev.fr",
            }
        )
