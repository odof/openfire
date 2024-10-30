# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

from freezegun import freeze_time

from odoo.addons.of_account.tests.common import TestOFAccountCommon


@freeze_time("2024-12-12 09:00:00")
class TestOFWizvilleHistory(TestOFAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.history_model = cls.env["of.wizville.history"]

        cls.env["ir.config_parameter"].set_param("of.wizville.base.wizville_sftp_host", "host_test")
        cls.env["ir.config_parameter"].set_param("of.wizville.base.wizville_sftp_port", 21)
        cls.env["ir.config_parameter"].set_param("of.wizville.base.wizville_sftp_user", "user_test")
        cls.env["ir.config_parameter"].set_param("of.wizville.base.wizville_sftp_password", "password_test")
        cls.env["ir.config_parameter"].set_param(
            "of.wizville.base.wizville_sftp_pickup_directory", "/mock/remote/directory/pickup"
        )
        cls.env["ir.config_parameter"].set_param(
            "of.wizville.base.wizville_sftp_deposit_directory", "/mock/remote/directory/deposit"
        )
        cls.env["ir.config_parameter"].set_param("of.wizville.base.wizville_import_filename_prefix", "'mock_import'")

        cls.env["ir.config_parameter"].set_param(
            "of.wizville.base.wizville_export_filename", "f'export_{company_code}'"
        )
        cls.company_fr.of_wizville_code = "TEST123"

        # Simulated CSV data (importation)
        # Contact data get from Faker libs (not real contact)
        header = [
            "Auteur",
            "ID_client",
            "Code_magasin",
            "Email",
            "Q1_Globalement_avezvous_ete_satisfaite_de_votre_experience_avec_Magasin__##question_78269##",
            "Q2_Recommanderiezvous_JOTUL_a_votre_entourage__##question_77901##;Date_de_facturation",
            "Date",
        ]
        cls.mock_import_csv_data = f"""{';'.join(header)}
LECOMTE;5497;jotul-valence;hugues.lecomte@openfire.fr;10;10;2024-03-22 00:00:00;25/03/24 11:39
ROBERT;10280;jotul-brive-la-gaillarde;frédérique.robert@openfire.fr;10;10;2024-03-22 00:00:00;25/03/24 11:29
JACOB;7008;jotul-bourges;élodie.jacob@openfire.fr;9;9;2024-03-21 00:00:00;24/03/24 19:15
MAHE;;jotul-vienne;michelle.mahe@openfire.fr;10;10;2024-03-12 00:00:00;24/03/24 15:12
LEGROS;;jotul-vienne;jeanne.legros@openfire.fr;10;9;2024-03-05 00:00:00;24/03/24 12:23
PERRIN;;jotul-perpignan;agnès.perrin@openfire.fr;10;10;2024-02-14 00:00:00;23/03/24 00:15
BERNARD;;jotul-perpignan;laure.bernard@openfire.fr;8;8;2024-03-12 00:00:00;22/03/24 16:45
RAYMOND;;jotul-perpignan;philippine.raymond@openfire.fr;10;10;2024-03-13 00:00:00;22/03/24 16:10
JOLY;;jotul-vienne;stéphanie.joly@openfire.fr;9;9;2024-02-01 00:00:00;22/03/24 11:42
DUBOIS;;jotul-vienne;timothée.dubois@openfire.fr;10;10;2024-02-08 00:00:00;22/03/24 11:13
DURAND;17632;jotul-la-primaube;daniel.durand@openfire.fr;7;7;2024-03-16 00:00:00;22/03/24 06:49
GÉRARD;;jotul-perpignan;chantal.gérard@openfire.fr10;10;2024-01-05 00:00:00;19/03/24 19:05
PONS;;jotul-saint-clair;sylvie.pons@openfire.fr;10;10;2024-02-07 00:00:00;19/03/24 16:24
MARTINEAU;;jotul-perpignan;emmanuel.martineau@openfire.fr;10;10;2024-02-01 00:00:00;19/03/24 14:28
JEAN;;jotul-perpignan;alexandria.jean@openfire.fr;10;10;2024-01-11 00:00:00;19/03/24 11:23
BERTHELOT;1748;jotul-dijon;andré.berthelot@openfire.fr;10;10;2024-03-12 00:00:00;19/03/24 08:59
PAUL;510;jotul-saumur;alfred.paul@openfire.fr;9;9;2024-03-12 00:00:00;18/03/24 17:05
LEBRUN;;jotul-saint-clair;maggie.lebrun@openfire.fr;10;10;2024-01-17 00:00:00;18/03/24 13:33
HERNANDEZ;;jotul-saint-clair;michelle.hernandez@openfire.fr;10;10;2024-02-01 00:00:00;18/03/24 13:14
"""  # noqa E231, E702
        cls.mock_import_csv_encoded = base64.b64encode(cls.mock_import_csv_data.encode("utf-8"))

        cls.mock_export_csv_data = f"""{';'.join(header)}
JACOB;7008;jotul-bourges;élodie.jacob@openfire.fr;2024-03-21 00:00:00;24/03/24 19:15;9;9
"""  # noqa E231, E702
        cls.mock_export_csv_encoded = base64.b64encode(cls.mock_export_csv_data.encode("utf-8"))

    def setUp(self):
        super().setUp()

    @patch("odoo.addons.of_wizville_base.models.of_wizville_history.OFWizvilleHistory._get_sftp_connection")
    def test_01_import_wizville_file(self, mock_get_sftp_connection):
        """Wizville file import test.
        Based on the CSV data, we need to generate 1 file import line in the history which, once validated, will
        generate 9 file export lines.
        """
        filename = f"mock_import_{datetime.now().strftime('%Y-%m-%d')}.csv"

        # Mock SFTP client, `listdir_attr` et `get`
        mock_sftp_client = MagicMock()
        mock_get_sftp_connection.return_value.__enter__.return_value = mock_sftp_client

        mock_sftp_client.listdir_attr.return_value = [MagicMock(filename=filename)]

        def mock_sftp_get(remote_path, local_path):
            with open(local_path, "w") as f:
                f.write(self.mock_import_csv_data)

        mock_sftp_client.get.side_effect = mock_sftp_get

        # Import
        self.history_model.with_context(of_no_commit=True).get_file_wizville()

        # Check import line created
        imported_records = self.history_model.search([("type", "=", "import")])
        self.assertEqual(len(imported_records), 1)
        self.assertEqual(imported_records.name, filename)
        self.assertEqual(base64.b64decode(imported_records.file).decode("utf-8"), self.mock_import_csv_data)

        # Integrate the imported file
        imported_records[0].action_button_integrate_wizville_file()

        # Check export lines generated
        export_history = self.history_model.search([("type", "=", "export")])
        self.assertEqual(len(export_history), 9)

        # List of expected stores
        expected_stores = [
            "jotul-valence",
            "jotul-brive-la-gaillarde",
            "jotul-bourges",
            "jotul-vienne",
            "jotul-perpignan",
            "jotul-la-primaube",
            "jotul-saint-clair",
            "jotul-dijon",
            "jotul-saumur",
        ]
        for record, store_code in zip(export_history, expected_stores):
            self.assertEqual(record.name, f"export_{store_code}")
            self.assertEqual(record.export_date, datetime.now().date())
            self.assertFalse(record.is_export_done)

        # Limit case: empty file should not create a line
        mock_sftp_client.get.side_effect = lambda remote_path, local_path: open(local_path, "w").close()
        self.history_model.with_context(of_no_commit=True).get_file_wizville()
        self.assertFalse(self.history_model.search([("type", "=", "import"), ("name", "=", "mock_import_empty.csv")]))

    @patch("odoo.addons.of_wizville_base.models.of_wizville_history.OFWizvilleHistory._get_sftp_connection")
    def test_02_export_wizville_file(self, mock_get_sftp_connection):
        """Test exporting a Wizville file via SFTP."""
        # Create an history line
        export_record = self.history_model.create(
            {
                "type": "export",
                "name": "mock_export.csv",
                "is_export_done": False,
            }
        )

        # Create an attachment to upload
        self.env["ir.attachment"].create(
            {
                "name": "mock_export.csv",
                "res_model": "of.wizville.history",
                "res_id": export_record.id,
                "res_field": "file",
                "store_fname": "mock_export.csv",
                "datas": self.mock_export_csv_encoded,
            }
        )

        # Mock SFTP client and `put`
        mock_sftp_client = MagicMock()
        mock_get_sftp_connection.return_value.__enter__.return_value = mock_sftp_client

        # Simulate upload behavior
        uploaded_files = {}

        def mock_sftp_put(local_path, remote_path):
            with open(local_path, "r") as f:
                uploaded_files[remote_path] = f.read()

        mock_sftp_client.put.side_effect = mock_sftp_put

        # Export file
        export_record.action_button_put_file_wizville()

        # Check exported content
        remote_filepath = "/mock/remote/directory/deposit/mock_export.csv"
        self.assertIn(remote_filepath, uploaded_files)
        self.assertEqual(uploaded_files[remote_filepath], self.mock_export_csv_data)
        self.assertTrue(export_record.is_export_done)
