# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64
import json
import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class ExportESBWizard(models.TransientModel):
    _name = 'of.esb.export.wizard'

    trigger_id = fields.Many2one(comodel_name='of.esb.trigger', string="Trigger")
    export_file = fields.Binary()
    filename = fields.Char()
    with_connexion = fields.Boolean()
    with_security = fields.Boolean()

    def action_export_json(self):
        # on export les triggers, extracts, transforms et loads avec le même uuid
        uuid = self.trigger_id.uuid
        triggers = self.env['of.esb.trigger'].search([('uuid', '=', uuid)])
        extracts = self.env['of.esb.extract'].search([('uuid', '=', uuid)])
        rules = self.env['of.esb.rule'].search([('uuid', '=', uuid)])

        res = {
            'triggers': triggers.action_export_json(
                parser=[
                    'name',
                    'uuid',
                    'is_operating_data',
                    'ttype',
                    'public',
                ]
            ),
            'extracts': extracts.action_export_json(
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
                ]
            ),
            'rules': rules.action_export_json(
                parser=[
                    'name',
                    'ttype',
                    'channel',
                    ('type_bus', ['name']),
                    ('service_id', ['name', 'exec_active', 'ttype', 'uuid', 'code']),
                    'uuid',
                ]
            ),
        }
        logger.info(res)

        self.filename = f"{self.trigger_id.name}.json"

        self.export_file = base64.b64encode(json.dumps(res).encode())

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/of.esb.export.wizard/%s/export_file/%s?download=true' % (self.id, self.filename),
        }
