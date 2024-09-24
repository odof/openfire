# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64
import json

from odoo import fields, models


class ImportESBWizard(models.TransientModel):
    _name = 'of.esb.import.wizard'

    import_file = fields.Binary()

    def action_import_json(self):
        data = base64.b64decode(self.import_file)
        data = json.loads(data)

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
        if type(triggers) is dict:
            triggers = [triggers]

        for trigger in triggers:
            if xml_id:
                record = self.env['of.esb.trigger'].browse(xml_id.res_id)
                record.write(trigger)
            else:
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
        if type(extracts) is dict:
            extracts = [extracts]

        for extract in extracts:
            if xml_id:
                record = self.env['of.esb.extract'].browse(xml_id.res_id)
                record.write(trigger)
            else:
                self.env['of.esb.extract'].create(extract)
