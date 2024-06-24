# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json

from odoo import fields, models


class ExportESBWizard(models.TransientModel):
    _name = "of.esb.export.wizard"
    _description = "Export ESB Data"

    trigger_id = fields.Many2one(comodel_name="of.esb.trigger", string="Trigger")
    export_file = fields.Binary()
    filename = fields.Char()

    def action_button_export_json(self):
        return self.action_export_json()

    def action_export_json(self):
        """
        Export triggers and extracts data to a JSON file.
        We export triggers, extracts, transforms, and loads with the same UUID.
        Transform and load data are nested in the extract data.

        Returns:
            dict: An action dictionary to trigger the download of the exported JSON file.
        """
        export_uuid = self.trigger_id.uuid
        triggers = self.env["of.esb.trigger"].search([("uuid", "=", export_uuid)])
        extracts = self.env["of.esb.extract"].search([("uuid", "=", export_uuid)])

        # Trigger data to extract
        trigger_parser = [
            "name",
            "uuid",
            "is_operating_data",
            "ttype",
            "public",
        ]

        # Extract data to extract
        extract_parser = [
            "name",
            "uuid",
            (
                "lines",
                [
                    "type_data",
                    "code",
                    "data",
                    (
                        "transform_id",
                        [
                            "name",
                            "uuid",
                            "code",
                            (
                                "load_id",
                                [
                                    "name",
                                    "uuid",
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]

        # Export data
        json_data = {
            "triggers": triggers.action_export_json(parser=trigger_parser),
            "extracts": extracts.action_export_json(parser=extract_parser),
        }

        self.filename = f"{self.trigger_id.name}.json"
        self.export_file = base64.b64encode(json.dumps(json_data).encode())

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/of.esb.export.wizard/{self.id}/export_file/{self.filename}?download=true",
        }
