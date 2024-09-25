# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64
import json

from odoo import fields, models


class ExportESBWizard(models.TransientModel):
    _name = 'of.esb.export.wizard'

    trigger_id = fields.Many2one(comodel_name='of.esb.trigger', string="Trigger")
    export_file = fields.Binary()
    filename = fields.Char()

    def action_export_json(self):
        # on export les triggers, extracts, transforms et loads avec le même uuid
        uuid = self.trigger_id.uuid
        triggers = self.env['of.esb.trigger'].search([('uuid', '=', uuid)])
        extracts = self.env['of.esb.extract'].search([('uuid', '=', uuid)])
        # Les transforms et loads étant lié plus ou moins directement avec les extracts,
        # pas besoin de les ajouter dans l'export

        trigger_parser = [
            'name',
            'uuid',
            'is_operating_data',
            'ttype',
            'public',
        ]

        extract_parser = [
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
        ]

        res = {
            'triggers': triggers.action_export_json(parser=trigger_parser),
            'extracts': extracts.action_export_json(parser=extract_parser),
        }

        self.filename = f"{self.trigger_id.name}.json"

        self.export_file = base64.b64encode(json.dumps(res).encode())

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/of.esb.export.wizard/%s/export_file/%s?download=true' % (self.id, self.filename),
        }
