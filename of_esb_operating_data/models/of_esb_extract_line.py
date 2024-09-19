# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one

logger = logging.getLogger(__name__)


class ESBExtractLine(models.Model):
    _name = 'of.esb.extract.line'
    _rec_name = 'connection_id'

    connection_id = fields.Many2one(comodel_name='of.esb.connection', string="Connection", required=True)
    data = fields.Text()
    code = fields.Text(required=True, default=lambda r: r._default_code())
    transform_id = fields.Many2one(comodel_name='of.esb.transform', string="Transform", required=True)
    extract_id = fields.Many2one(comodel_name='of.esb.extract', string="Extract", ondelete='cascade')
    example = fields.Text(compute="_compute_example")
    type_data = fields.Selection(selection=[('code', 'Code'), ('data', 'Data')], default='code')

    def _default_code(self):
        return """
# Vous retrouvez dans la variable data, toutes les données qui viennent de l'étape précédente
# Vous devez retourner dans la variable result, tout ce qui ira dans l'étape suivante"""

    @api.depends('connection_id')
    def _compute_example(self):
        for record in self:
            if record.connection_id:
                record.example = record.connection_id.get_in_example()
            else:
                record.example = "#TODO"

    def execute(self, args):
        for record in self:
            result = {}
            exec(
                record.code,
                {'data': json.loads(args.in_data), 'env': self.env, 'logger': logger, 'self': record},
                result,
            )
            record.data = json.dumps(result.get('result', []), indent=2)

    @api.model_create_multi
    def create(self, list_vals):
        for vals in list_vals:
            if data := vals.get("data"):
                vals["data"] = json.dumps(json.loads(data), indent=2)

        list_res = super().create(list_vals)

        for res in list_res:
            # on ajoute la rule et le service qui vont bien
            value_service = {
                'name': f"Transform : {res.extract_id.name}",
                'code': f"""# on appelle la fonction transform avec le même UUID
self.env['of.esb.transform'].search([('uuid','=','{res.extract_id.uuid}')]).execute(args)
""",
                'ttype': 'user',
            }
            service = self.env['of.esb.service'].create(value_service)

            value_rule = {
                'name': f"Extract : {res.extract_id.name}",
                'ttype': 'user',
                'channel_bus': slugify_one(res.extract_id.name),
                'type_bus': self.env.ref('of_esb_operating_data.type_transform').id,
                'service': service.id,
            }
            self.env['of.esb.rule'].create(value_rule)

        return list_res

    def write(self, vals):
        if data := vals.get("data"):
            vals['data'] = json.dumps(json.loads(data), indent=2)

        return super().write(vals)
