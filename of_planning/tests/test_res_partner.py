# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestResPartner(TestOFPlanningCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # delete the existing sectors if any because they may interfere with the tests
        cls.env["of.sector"].search(
            [("id", "not in", [cls.sector_tech_com.id, cls.sector_com.id, cls.sector_tech.id])]
        ).unlink()

    def test_01_compute_of_sector_id_nok(self):
        """Test that the sectors are not computed when the automatic sectors are disabled"""
        self.env["res.config.settings"].create({"of_automatic_sectors": False}).execute()
        partner = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "is_company": True,
                "street": "1, rue du Poêle",
                "zip": "35000",
                "city": "Rennes",
                "phone": "02 99 99 99 99",
            }
        )
        self.assertFalse(partner.of_tech_sector_id)
        self.assertFalse(partner.of_com_sector_id)

    def test_02_compute_of_sector_tech_ok_com_ok(self):
        """Test that the sectors are computed correctly when the automatic sectors are enabled.
        `sector_tech_com` : 35000 - 35300, 35500 - 35800
        """
        self.env["res.config.settings"].create({"of_automatic_sectors": True}).execute()

        partner = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "is_company": True,
                "street": "1, rue du Poêle",
                "zip": "35750",
                "city": "Pacé",
                "phone": "02 99 99 99 99",
            }
        )

        self.assertEqual(partner.of_tech_sector_id, self.sector_tech_com)
        self.assertEqual(partner.of_com_sector_id, self.sector_tech_com)

        # Test that the sectors are recomputed when the zip code is changed
        partner.write({"zip": "35400", "city": "Saint-Malo"})
        self.assertEqual(partner.of_tech_sector_id, self.env["of.sector"])

    def test_03_compute_of_sector_tech_nok_com_nok(self):
        """Test that the sectors are computed correctly when the automatic sectors are enabled.
        `sector_com` : 35301 - 35400
        """
        self.env["res.config.settings"].create({"of_automatic_sectors": True}).execute()

        partner = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "is_company": True,
                "street": "1, rue du Poêle",
                "zip": "35301",
                "city": "Fougères",
                "phone": "02 99 99 99 99",
            }
        )
        self.assertFalse(partner.of_tech_sector_id)
        self.assertEqual(partner.of_com_sector_id, self.sector_com)

        # Test that the sectors are recomputed when the zip code is changed
        partner.write({"zip": "35400", "city": "Saint-Malo"})
        self.assertEqual(partner.of_tech_sector_id, self.env["of.sector"])

    def test_04_compute_of_sector_tech_ok_com_nok(self):
        """Test that the sectors are computed correctly when the automatic sectors are enabled.
        `sector_tech` : 35801 - 35900
        """
        self.env["res.config.settings"].create({"of_automatic_sectors": True}).execute()

        partner = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "is_company": True,
                "street": "1, rue du Poêle",
                "zip": "35850",
                "city": "Gévezé",
                "phone": "02 99 99 99 99",
            }
        )
        self.assertEqual(partner.of_tech_sector_id, self.sector_tech)
        self.assertFalse(partner.of_com_sector_id)

        # Test that the sectors are recomputed when the zip code is changed
        partner.write({"zip": "35400", "city": "Saint-Malo"})
        self.assertEqual(partner.of_tech_sector_id, self.env["of.sector"])
