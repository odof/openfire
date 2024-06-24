# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import uuid

from odoo import fields, models


class ESBLoad(models.Model):
    _name = "of.esb.load"
    _description = "ESB Load"

    name = fields.Char()
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    connection_id = fields.Many2one(comodel_name="of.esb.connection", string="Connection")
    uuid = fields.Char(default=uuid.uuid4())

    def execute(self, args):
        for record in self:
            properties = json.loads(args.properties)
            data = json.loads(args.in_data)

            in_data = [
                {
                    "connection_id": record.connection_id.id,
                    "data": data.get("data", {}),
                }
            ]

            bus_data = {"data": in_data, "type": record.connection_id.ttype, "uuid": properties.get("uuid")}

            self.env["of.esb.bus"].send_bus(
                ttype=self.env.ref("of_esb.type_internal"),
                channel="set_data",
                data=bus_data,
                properties={"uuid": properties.get("uuid")},
            )
