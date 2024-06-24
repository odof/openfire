# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import uuid

from odoo import fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one


class ESBExtract(models.Model):
    _name = "of.esb.extract"

    name = fields.Char()
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    lines = fields.One2many(comodel_name="of.esb.extract.line", inverse_name="extract_id")
    uuid = fields.Char(default=uuid.uuid4())

    def execute(self, args):
        for record in self:
            properties = json.loads(args.properties)

            for line in record.lines:
                if line.type_data == "code":
                    line.execute(args)
                    # ici, on a le résultat de l'exécution dans le champs data
                in_data = [
                    {
                        "connection_id": line.connection_id.id,
                        "data": json.loads(line.data),
                        "bus_type": self.env.ref("of_esb_operating_data.type_transform").name,
                        "bus_channel": slugify_one(line.transform_id.name),
                        "args": args.in_data,
                    }
                ]

                data = {"data": in_data, "type": line.connection_id.ttype, "uuid": properties.get("uuid")}
                self.env["of.esb.bus"].send_bus(
                    ttype=self.env.ref("of_esb.type_internal"),
                    channel="get_data",
                    data=data,
                    properties={"uid": properties.get("uuid")},
                )
