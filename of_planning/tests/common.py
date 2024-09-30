# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_sale.tests.common import TestOFSaleCommon

BRUZ_JOLY_LAT_LNG = ("48.0243671", "-1.7475088")
CESSON_VILAINE_LAT_LNG = ("48.1160448", "-1.6058050")


class TestOFPlanningCommon(TestOFSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Supplier data
        cls.supplier_stove = cls.env["res.partner"].create(
            {
                "name": "Stove Supplier 1",
                "is_company": True,
                "street": "1, rue du Poêle",
                "zip": "35000",
                "city": "Rennes",
                "phone": "02 99 99 99 99",
            }
        )

        # Product and brand data
        cls.brand_stove = cls.env["of.product.brand"].create(
            {
                "name": "Stove Brand 1",
                "code": "SB1",
                "partner_id": cls.supplier_stove.id,
            }
        )

        cls.product_wood_stove = cls.env["product.product"].create(
            {
                "name": "Poêle à bois",
                "type": "product",
                "list_price": 1000,
                "brand_id": cls.brand_stove.id,
                "description_sale": "Superbe Poêle à bois de marque Stove Brand 1",
            }
        )

        cls.product_ash_vacuum_cleaner = cls.env["product.product"].create(
            {
                "name": "Aspirateur à cendres",
                "type": "product",
                "list_price": 125,
                "brand_id": cls.brand_stove.id,
                "description_sale": "Aspirateur à cendres pour poêle à bois",
            }
        )

        # Tasks data
        cls.task_sweeping = cls.env["of.planning.task"].create(
            {
                "name": "Ramonage",
                "duration": 1.5,
                "description": "Tâche de ramonage",
            }
        )

        cls.task_installation = cls.env["of.planning.task"].create(
            {
                "name": "Installation poêle à bois",
                "duration": 8,
                "description": "Tâche d'installation de poêle à bois",
            }
        )

        cls.partner_jean = cls.env["res.partner"].create(
            {
                "name": "Jean",
                "street": "25 Cr de la Vilaine",
                "zip": "35510",
                "city": "Cesson-Sévigné",
                "email": "jean@test.fr",
                "partner_latitude": CESSON_VILAINE_LAT_LNG[0],
                "partner_longitude": CESSON_VILAINE_LAT_LNG[1],
            }
        )
        cls.partner_bruce = cls.env["res.partner"].create(
            {
                "name": "Bruce",
                "street": "3 Pl. du Dr Joly",
                "zip": "35710",
                "city": "Bruz",
                "email": "jean@test.fr",
                "partner_latitude": BRUZ_JOLY_LAT_LNG[0],
                "partner_longitude": BRUZ_JOLY_LAT_LNG[1],
            }
        )

        # Employees data
        cls.employee_tech_johnny = cls.env["hr.employee"].create(
            {
                "name": "Johnny Crash",
                "user_id": cls.env["res.users"]
                .create(
                    {
                        "name": "Johnny Crash",
                        "login": "johnny.crash",
                    }
                )
                .id,
                "of_all_tasks": True,
                "of_is_operator": True,
            }
        )
        cls.employee_tech_bruce = cls.env["hr.employee"].create(
            {
                "name": "Bruce Quivis",
                "user_id": cls.env["res.users"]
                .create(
                    {
                        "name": "Bruce Quivis",
                        "login": "bruce.quivis",
                    }
                )
                .id,
                "of_start_address_id": cls.partner_bruce.id,
                "of_return_address_id": cls.partner_bruce.id,
                "of_task_ids": [Command.set([cls.task_sweeping.id, cls.task_installation.id])],
                "of_is_operator": True,
            }
        )

        cls.employee_tech_jean = cls.env["hr.employee"].create(
            {
                "name": "Jean Dugratin",
                "user_id": cls.env["res.users"]
                .create(
                    {
                        "name": "Jean Dugratin",
                        "login": "jean.dugratin",
                    }
                )
                .id,
                "of_start_address_id": cls.partner_jean.id,
                "of_return_address_id": cls.partner_jean.id,
                "of_task_ids": [Command.set([cls.task_sweeping.id])],
                "of_is_operator": True,
                "of_all_tasks": False,
            }
        )

        # Intervention templates data
        cls.template_installation = cls.env["of.planning.intervention.template"].create(
            {
                "name": "Installation poêle à bois",
                "code": "PAB",
                "task_id": cls.task_installation.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_ash_vacuum_cleaner.id,
                            "qty": 1,
                            "price_unit": 125.0,
                        }
                    )
                ],
            }
        )

        cls.template_sweeping = cls.env["of.planning.intervention.template"].create(
            {
                "name": "Ramonage",
                "code": "RAM",
                "task_id": cls.task_sweeping.id,
            }
        )

        # Sectors data
        cls.sector_tech_com = cls.env["of.sector"].create(
            {
                "name": "Sector 1 (technical and commercial)",
                "code": "STC",
                "type": "technical_commercial",
                "zip_range_ids": [
                    Command.create(
                        {
                            "zip_code_min": "35000",
                            "zip_code_max": "35300",
                        }
                    ),
                    Command.create(
                        {
                            "zip_code_min": "35500",
                            "zip_code_max": "35800",
                        }
                    ),
                ],
            }
        )

        cls.sector_com = cls.env["of.sector"].create(
            {
                "name": "Sector 2 (commercial only)",
                "code": "SC",
                "type": "commercial",
                "zip_range_ids": [
                    Command.create(
                        {
                            "zip_code_min": "35301",
                            "zip_code_max": "35400",
                        }
                    ),
                ],
            }
        )

        cls.sector_tech = cls.env["of.sector"].create(
            {
                "name": "Sector 3 (technical only)",
                "code": "ST",
                "type": "technical",
                "zip_range_ids": [
                    Command.create(
                        {
                            "zip_code_min": "35801",
                            "zip_code_max": "35900",
                        }
                    ),
                ],
            }
        )
