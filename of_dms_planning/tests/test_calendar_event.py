# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from dateutil.relativedelta import relativedelta

from odoo import Command, fields

from .common import TestOFDMSPlanningCommon


class TestOFDMSPlanningCalendarEvent(TestOFDMSPlanningCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.events = (
            cls.env["calendar.event"]
            .create(
                [
                    {
                        "name": "Test Event 1",
                        "of_type": "intervention",
                        "start": fields.Datetime.now(),
                        "stop": fields.Datetime.now() + relativedelta(hours=1),
                        "of_company_id": cls.company_fr.id,
                        "of_employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                        "of_partner_id": cls.customer_a.id,
                    },
                    {
                        "name": "Test Event 2",
                        "of_type": "intervention",
                        "start": fields.Datetime.now() + relativedelta(days=1),
                        "stop": fields.Datetime.now() + relativedelta(days=1, hours=1),
                        "of_company_id": cls.company_fr.id,
                        "of_employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                        "of_partner_id": cls.supplier_a.id,
                    },
                    {
                        "name": "Test Event 3",
                        "of_type": "intervention",
                        "start": fields.Datetime.now() + relativedelta(days=2),
                        "stop": fields.Datetime.now() + relativedelta(days=2, hours=1),
                        "of_company_id": cls.company_fr.id,
                        "of_employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                        "of_partner_id": cls.supplier_b.id,
                    },
                ]
            )
            .sorted("id")
        )

        cls.attachments = cls.create_attachments(
            [
                {
                    "name": "test.txt",
                    "res_model": "calendar.event",
                    "res_id": cls.events[0].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "calendar.event",
                    "res_id": cls.events[1].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "calendar.event",
                    "res_id": cls.events[2].id,
                    "datas": cls.content_base64(),
                },
            ]
        ).sorted("id")

        cls.real_files = cls.file_model.search(
            [("of_type", "=", "real"), ("attachment_id", "in", cls.attachments.ids)]
        ).sorted("id")
        cls.virtual_files = cls.file_model.search(
            [
                ("of_type", "=", "virtual"),
                ("of_virtual_res_model", "=", cls.env.ref("calendar.model_calendar_event").id),
                ("of_virtual_res_id", "in", cls.events.ids),
            ]
        ).sorted("id")

    def test_01_create_attachment_planning(self):
        """Test that the attachment are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "calendar.event",
                    "res_id": self.events[0].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "calendar.event",
                    "res_id": self.events[1].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "calendar.event",
                    "res_id": self.events[2].id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_virtual_files_planning(self):
        """Test that the virtual files are correctly created"""
        self.assertRecordValues(
            self.virtual_files,
            [
                {
                    "of_type": "virtual",
                    "name": f"Partner A {str(self.events[0].start.date()).replace('/', '-')}.pdf",
                    "directory_id": self.planning_directories[0].id,
                    "attachment_id": False,
                    "res_model": "calendar.event",
                    "of_virtual_res_model": self.env.ref("calendar.model_calendar_event").id,
                    "of_virtual_res_id": self.events[0].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"""Fiche d'intervention - Test Event 1 - {
                        str(self.events[0].start.date()).replace('/', '-')
                    }.pdf""",
                    "directory_id": self.planning_directories[0].id,
                    "attachment_id": False,
                    "res_model": "calendar.event",
                    "of_virtual_res_model": self.env.ref("calendar.model_calendar_event").id,
                    "of_virtual_res_id": self.events[0].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"Supplier A {str(self.events[1].start.date()).replace('/', '-')}.pdf",
                    "directory_id": self.planning_directories[1].id,
                    "attachment_id": False,
                    "res_model": "calendar.event",
                    "of_virtual_res_model": self.env.ref("calendar.model_calendar_event").id,
                    "of_virtual_res_id": self.events[1].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"""Fiche d'intervention - Test Event 2 - {
                        str(self.events[1].start.date()).replace('/', '-')
                    }.pdf""",
                    "directory_id": self.planning_directories[1].id,
                    "attachment_id": False,
                    "res_model": "calendar.event",
                    "of_virtual_res_model": self.env.ref("calendar.model_calendar_event").id,
                    "of_virtual_res_id": self.events[1].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"Supplier B {str(self.events[2].start.date()).replace('/', '-')}.pdf",
                    "directory_id": self.planning_directories[2].id,
                    "attachment_id": False,
                    "res_model": "calendar.event",
                    "of_virtual_res_model": self.env.ref("calendar.model_calendar_event").id,
                    "of_virtual_res_id": self.events[2].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"""Fiche d'intervention - Test Event 3 - {
                        str(self.events[2].start.date()).replace('/', '-')
                    }.pdf""",
                    "directory_id": self.planning_directories[2].id,
                    "attachment_id": False,
                    "res_model": "calendar.event",
                    "of_virtual_res_model": self.env.ref("calendar.model_calendar_event").id,
                    "of_virtual_res_id": self.events[2].id,
                },
            ],
        )

    def test_03_create_real_files_planning(self):
        """Test that the real files are correctly created"""
        self.assertRecordValues(
            self.real_files,
            [
                {
                    "of_type": "real",
                    "name": "test.txt",
                    "directory_id": self.planning_directories[0].id,
                    "attachment_id": self.attachments[0].id,
                    "res_model": "calendar.event",
                },
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.planning_directories[1].id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "calendar.event",
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.planning_directories[2].id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "calendar.event",
                },
            ],
        )

    def test_04_update_directory_planning(self):
        """Test that the directories are correctly updated"""
        self.assertRecordValues(
            [
                self.customer_a.of_dms_directory_id,
                self.supplier_a.of_dms_directory_id,
                self.supplier_b.of_dms_directory_id,
            ],
            [
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.planning_directories[0].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.planning_directories[1].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.planning_directories[2].ids,
                },
            ],
        )

    def test_05_update_subdirectory_planning(self):
        """Test that the subdirectories are correctly updated"""
        self.assertRecordValues(
            self.planning_directories,
            [
                {
                    "active": True,
                    "count_files": 3,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[0].id,
                        self.virtual_files[1].id,
                        self.real_files[0].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Interventions",
                    "res_model": "calendar.event",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": True,
                    "count_files": 3,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[2].id,
                        self.virtual_files[3].id,
                        self.real_files[1].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Interventions",
                    "res_model": "calendar.event",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": True,
                    "count_files": 3,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[4].id,
                        self.virtual_files[5].id,
                        self.real_files[2].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Interventions",
                    "res_model": "calendar.event",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": False,
                },
            ],
        )
