# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestOFEquipmentCommon(TestOFPlanningCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # == Create Tasks, Equipments and Equipment Intervention Report Templates ==
        # Tasks
        cls.task_aftersales_service = cls.env["of.planning.task"].create(
            {
                "name": "SAV",
                "duration": 3,
            }
        )

        # Generic equipments
        cls.equipment_wood_stove = cls.env["of.equipment"].create(
            {
                "name": "CA/WS00001",
                "product_id": cls.product_wood_stove.id,
                "customer_id": cls.customer_a.id,
                "site_address_id": cls.customer_a.id,
            }
        )
        cls.equipment_ash_vacuum_cleaner = cls.env["of.equipment"].create(
            {
                "name": "CA/AVC00001",
                "product_id": cls.product_ash_vacuum_cleaner.id,
                "customer_id": cls.customer_a.id,
                "site_address_id": cls.customer_a.id,
            }
        )

        # Equipment Intervention Report Templates
        cls.eq_report_tmpl_maintenance = cls.env["of.equipment.intervention.report.template"].create(
            {
                "name": "Entretien",
                "task_id": cls.task_sweeping.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_consu_a.id,
                            "qty": 1,
                            "price_unit": 150,
                        }
                    )
                ],
            }
        )
        cls.eq_report_tmpl_aftersales_service = cls.env["of.equipment.intervention.report.template"].create(
            {
                "name": "SAV",
                "task_id": cls.task_aftersales_service.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_consu_b.id,
                            "qty": 1,
                            "price_unit": 200,
                        }
                    )
                ],
            }
        )
        # Intervention templates
        cls.template_maintenance_equipment = cls.env["of.planning.intervention.template"].create(
            {
                "name": "Entretien équipement",
                "code": "ENT_EQ",
                "task_id": cls.task_sweeping.id,
                "type_id": cls.env.ref("of_service.of_service_request_type_maintenance").id,
                "default_equipment_report_tmpl_id": cls.eq_report_tmpl_maintenance.id,
            }
        )

        cls.template_installation_equipment = cls.env["of.planning.intervention.template"].create(
            {
                "name": "Installation équipement",
                "code": "INST_EQ",
                "task_id": cls.task_installation.id,
                "type_id": cls.env.ref("of_service.of_service_request_type_maintenance").id,
                "default_equipment_report_tmpl_id": cls.eq_report_tmpl_maintenance.id,
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

        # == Create Customers and Equipments ==
        # Create new customer Johnny Holiday
        cls.customer_johnny_holiday_mansion = cls.env["res.partner"].create(
            {
                "name": "Mansion",
                "street": "1 route du Rock",
                "zip": "35000",
                "city": "Rennes",
                "country_id": cls.env.ref("base.fr").id,
            }
        )
        cls.customer_johnny_holiday = cls.env["res.partner"].create(
            {
                "name": "Johnny Holiday",
                "street": "1 rue du Mississippi",
                "zip": "35000",
                "city": "Rennes",
                "is_company": True,
                "country_id": cls.env.ref("base.fr").id,
                "child_ids": [Command.set([cls.customer_johnny_holiday_mansion.id])],
            }
        )

        # Create 1 equipment for Johnny Holiday
        cls.equipment_wood_stove_jh = cls.env["of.equipment"].create(
            {
                "name": "JH/WS00001",
                "product_id": cls.product_wood_stove.id,
                "customer_id": cls.customer_johnny_holiday.id,
                "site_address_id": cls.customer_johnny_holiday.id,
            }
        )

        # Create new customer Johnny Crash
        cls.customer_johnny_crash_apartment = cls.env["res.partner"].create(
            {
                "name": "Appartement",
                "street": "4 rue de la Guitare",
                "zip": "35000",
                "city": "Rennes",
                "country_id": cls.env.ref("base.fr").id,
            }
        )
        cls.customer_johnny_crash_main_home = cls.env["res.partner"].create(
            {
                "name": "Maison",
                "street": "13 rue de l'Arkansas",
                "zip": "35000",
                "city": "Rennes",
                "country_id": cls.env.ref("base.fr").id,
            }
        )
        cls.customer_johnny_crash_country_home = cls.env["res.partner"].create(
            {
                "name": "Maison de campagne",
                "street": "21 rue de la Country",
                "zip": "35000",
                "city": "Rennes",
                "country_id": cls.env.ref("base.fr").id,
            }
        )
        cls.customer_johnny_crash = cls.env["res.partner"].create(
            {
                "name": "Johnny Crash",
                "street": "1 rue du Tennessee",
                "zip": "35000",
                "city": "Rennes",
                "is_company": True,
                "country_id": cls.env.ref("base.fr").id,
                "child_ids": [
                    Command.set(
                        [
                            cls.customer_johnny_crash_apartment.id,
                            cls.customer_johnny_crash_main_home.id,
                            cls.customer_johnny_crash_country_home.id,
                        ]
                    )
                ],
            }
        )

        # Create Equipments for Johnny Crash
        (
            cls.equipment_wood_stove_jc,
            cls.equipment_wood_stove_jc_apt,
            cls.equipment_wood_stove_jc_mh,
            cls.equipment_wood_stove_jc_ch,
            cls.equipment_ash_vacuum_cleaner_jc,
        ) = cls.env["of.equipment"].create(
            [
                {
                    "name": "JC/WS00001",
                    "product_id": cls.product_wood_stove.id,
                    "customer_id": cls.customer_johnny_crash.id,
                    "site_address_id": cls.customer_johnny_crash.id,
                },
                {
                    "name": "JC-APT/WS00002",
                    "product_id": cls.product_wood_stove.id,
                    "customer_id": cls.customer_johnny_crash.id,
                    "site_address_id": cls.customer_johnny_crash_apartment.id,
                },
                {
                    "name": "JC-MH/WS00003",
                    "product_id": cls.product_wood_stove.id,
                    "customer_id": cls.customer_johnny_crash.id,
                    "site_address_id": cls.customer_johnny_crash_main_home.id,
                },
                {
                    "name": "JC-CH/WS00004",
                    "product_id": cls.product_wood_stove.id,
                    "customer_id": cls.customer_johnny_crash.id,
                    "site_address_id": cls.customer_johnny_crash_country_home.id,
                },
                {
                    "name": "JC/AVC00001",
                    "product_id": cls.product_ash_vacuum_cleaner.id,
                    "customer_id": cls.customer_johnny_crash.id,
                    "site_address_id": cls.customer_johnny_crash.id,
                },
            ]
        )
