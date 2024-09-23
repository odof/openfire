# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64
import json
import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class ImportESBWizard(models.TransientModel):
    _name = 'of.esb.import.wizard'

    import_file = fields.Binary()

    def action_import_json(self):
        data = base64.b64decode(self.import_file)
        data = json.loads(data)

        logger.info(data)

        triggers, xml_id = self.env['of.esb.trigger'].action_import_json(
            data=data.get('triggers'),
            parser=[
                'name',
                'uuid',
                'is_operating_data',
                'ttype',
                'public',
            ],
        )
        logger.info(f"Triggers : {triggers}")
        for trigger in triggers:
            self.env["of.esb.trigger"].create(trigger)

        extracts, xml_id = self.env['of.esb.extract'].action_import_json(
            data=data.get('extracts'),
            parser=[
                'name',
                'uuid',
                (
                    'lines',
                    [
                        'type_data',
                        'code',
                        'data',
                        (
                            'transform_id',
                            [
                                'name',
                                'uuid',
                                'code',
                                (
                                    'load_id',
                                    [
                                        'name',
                                        'uuid',
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

        logger.info(f"Extracts: {extracts}")
        for extract in extracts:
            self.env['of.esb.extract'].create(extract)
