# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one

logger = logging.getLogger(__name__)


class ESBTrigger(models.Model):
    _inherit = 'of.esb.trigger'

    is_operating_data = fields.Boolean()
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")

    @api.model_create_multi
    def create(self, list_vals):
        # si on a is_operating_data dans le trigger,
        # on va forcer la création d'un extract, d'un load et d'un transform pour les lier automatiquement
        for vals in list_vals:
            if self.env.context.get('default_is_operating_data', False) or vals.get('is_operating_data', False):
                value_extract = {
                    'name': vals.get('name'),
                    'partner_id': vals.get('partner_id'),
                    'uuid': vals.get('uuid'),
                }
                self.env['of.esb.extract'].create(value_extract)
                value_load = {'name': vals.get('name'), 'partner_id': vals.get('partner_id'), 'uuid': vals.get('uuid')}
                load_id = self.env['of.esb.load'].create(value_load)
                value_transform = {
                    'name': vals.get('name'),
                    'partner_id': vals.get('partner_id'),
                    'load_id': load_id.id,
                    'uuid': vals.get('uuid'),
                    'code': "#",
                }
                self.env['of.esb.transform'].create(value_transform)
            # on va créer par trigger, une rule et un service pour y réagir
            value_service = {
                'name': f"Extract : {vals.get('name')}",
                'code': f"""# on appelle la fonction extract avec le même UUID
self.env['of.esb.extract'].search([('uuid','=','{vals.get('uuid')}')]).execute(args)
""",
                'ttype': 'user',
                'uuid': vals.get('uuid'),
            }
            service = self.env['of.esb.service'].create(value_service)

            value_rule = {
                'name': f"Trigger : {vals.get('name')}",
                'ttype': 'user',
                'channel_bus': slugify_one(vals.get('name')),
                'type_bus': self.env.ref('of_esb.type_webhook').id,
                'service': service.id,
                'uuid': vals.get('uuid'),
            }
            self.env['of.esb.rule'].create(value_rule)
        return super().create(list_vals)
