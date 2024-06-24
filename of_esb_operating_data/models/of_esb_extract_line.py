# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import json

from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one


class ESBExtractLine(models.Model):
    _name = 'of.esb.extract.line'
    _rec_name = 'connection_id'

    connection_id = fields.Many2one(comodel_name='of.esb.connection', string="Connection", required=True)
    data = fields.Text()
    transform_id = fields.Many2one(comodel_name='of.esb.transform', string="Transform", required=True)
    extract_id = fields.Many2one(comodel_name='of.esb.extract', string="Extract", ondelete='cascade')
    example = fields.Text(compute="_compute_example")

    @api.depends('connection_id')
    def _compute_example(self):
        for record in self:
            if record.connection_id:
                record.example = record.connection_id.get_in_example()
            else:
                record.example = "#TODO"

    @api.model_create_multi
    def create(self, list_vals):
        for vals in list_vals:
            if data := vals.get("data"):
                vals["data"] = json.dumps(ast.literal_eval(data), indent=2)

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
            vals['data'] = json.dumps(ast.literal_eval(data), indent=2)

        return super().write(vals)
