# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json

from odoo import fields, models


class ImportESBWizard(models.TransientModel):
    _name = "of.esb.import.wizard"
    _description = "Import ESB Data"

    import_file = fields.Binary()

    def action_button_import_json(self):
        return self.action_import_json()

    def action_import_json(self):
        """
        Imports JSON data for ESB triggers and extracts, creating or updating records as necessary.
        """
        data = base64.b64decode(self.import_file)
        json_data = json.loads(data)

        triggers = self.env["of.esb.trigger"].action_import_json(
            data=json_data.get("triggers"),
            parser=[
                "name",
                "uuid",
                "is_operating_data",
                "ttype",
                "public",
            ],
        )
        if type(triggers) is dict:
            triggers = [triggers]

        extracts = self.env["of.esb.extract"].action_import_json(
            data=json_data.get("extracts"),
            parser=[
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
            ],
        )
        if type(extracts) is dict:
            extracts = [extracts]

        # Process triggers and extracts
        self._process_triggers(triggers)
        self._process_extracts(extracts)

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _process_triggers(self, triggers):
        esb_trigger_obj = self.env["of.esb.trigger"]
        ir_model_data_obj = self.env["ir.model.data"]

        for trigger in triggers:
            if xml_id := trigger.get("xml_id"):
                record = esb_trigger_obj.browse(xml_id.res_id)
                record.write(trigger.get("value"))
            else:
                record = esb_trigger_obj.create(trigger.get("value"))
                # Création de l'xml_id pour les prochaines mises à jour
                ir_model_data_obj.create(
                    {
                        "name": trigger.get("name"),
                        "module": trigger.get("module"),
                        "model": record._name,
                        "res_id": record.id,
                        "noupdate": True,
                    }
                )

    def _process_extracts(self, extracts):
        esb_extract_obj = self.env["of.esb.extract"]
        ir_model_data_obj = self.env["ir.model.data"]

        for extract in extracts:
            if xml_id := extract.get("xml_id"):
                record = esb_extract_obj.browse(xml_id.res_id)
                record.write(extract.get("value"))
            else:
                record = esb_extract_obj.create(extract.get("value"))
                # Création de l'xml_id pour les prochaines mises à jour
                ir_model_data_obj.create(
                    {
                        "name": extract.get("name"),
                        "module": extract.get("module"),
                        "model": record._name,
                        "res_id": record.id,
                        "noupdate": True,
                    }
                )
