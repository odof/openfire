# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import uuid

from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one

logger = logging.getLogger(__name__)


class ESBTransform(models.Model):
    _name = 'of.esb.transform'

    name = fields.Char('Name')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    code = fields.Text(required=True, default=lambda r: r._default_code())
    load_id = fields.Many2one(comodel_name='of.esb.load', string="Load", required=True)
    uuid = fields.Char(default=lambda r: uuid.uuid4())
    example = fields.Text(compute="_compute_example")
    preview = fields.Text()

    def _default_code(self):
        return """
# Vous retrouvez dans la variable data, toutes les données qui viennent de l'étape précédente
# Vous devez retourner dans la variable result, tout ce qui ira dans l'étape suivante"""

    @api.depends('load_id')
    def _compute_example(self):
        for record in self:
            if record.load_id and record.load_id.connection_id:
                record.example = record.load_id.connection_id.get_out_example()
            else:
                record.example = "#Todo"

    def execute(self, args):
        for record in self:
            properties = json.loads(args.properties)
            result = {}
            exec(
                record.code,
                {'data': json.loads(args.in_data), 'env': self.env},
                result,
            )
            # on ne garde dans result que ce qui est contenu dans la variable result
            data = {'data': result.get('result', {}), 'uuid': properties.get('uuid')}
            self.env['of.esb.bus'].send_bus(
                ttype=self.env.ref('of_esb_operating_data.type_load'),
                channel=record.load_id.name,
                data=data,
                properties={'uuid': properties.get('uuid')},
            )

    def action_button_preview(self):
        # on lance une preview qu'on affiche ensuite
        # il faut retrouver l'extract juste avant le transform
        extract_line = self.env['of.esb.extract.line'].search([('transform_id', '=', self.id)], limit=1)
        # on retrouve la connection et on lance le connect
        self.preview = self.env['of.esb.service'].preview(extract_line.connection_id, json.loads(extract_line.data))

    @api.model_create_multi
    def create(self, list_vals):
        list_res = super().create(list_vals)
        for res in list_res:
            # on ajoute la rule et le service qui vont bien
            value_service = {
                'name': f"Load : {res.load_id.name}",
                'code': f"""# on appelle la fonction load avec le même UUID
self.env['of.esb.load'].search([('uuid','=','{res.load_id.uuid}')]).execute(args)
""",
                'ttype': 'user',
            }
            service = self.env['of.esb.service'].create(value_service)

            value_rule = {
                'name': f"Transform : {res.load_id.name}",
                'ttype': 'user',
                'channel_bus': slugify_one(res.load_id.name),
                'type_bus': self.env.ref('of_esb_operating_data.type_load').id,
                'service': service.id,
            }
            self.env['of.esb.rule'].create(value_rule)
        return list_res
