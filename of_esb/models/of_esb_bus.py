# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import json
import uuid

from odoo import api, fields, models


class ESBBus(models.Model):
    _name = "of.esb.bus"
    _description = "ESB Bus"
    _rec_name = "channel"

    channel = fields.Char()
    ttype = fields.Many2one(comodel_name="of.esb.type.bus", string="Type of bus")
    data = fields.Many2one(comodel_name="of.esb.data")
    uuid = fields.Char(default=lambda r: uuid.uuid4())
    date = fields.Datetime(default=fields.Datetime.now)

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        bus_records = super().create(vals_list)

        bus_records._handle_bus_rules()
        return bus_records

    def unlink(self):
        # on doit supprimer aussi la data
        for record in self:
            record.data.unlink()

        return super().unlink()

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @api.model
    def send_bus(self, ttype, channel, data, properties=None):
        """
        Sends data to the specified bus channel.

        Args:
            ttype (object): The type of bus.
            channel (str): The name of the channel.
            data (dict): A dictionary containing data to send into the bus.
            properties (dict, optional): Additional properties to be sent. Defaults to None.

        Returns:
            object: The created bus object.
        """
        if not properties:
            properties = {}
        value_data = {
            "in_data": json.dumps(data),
            "properties": json.dumps(properties),
        }
        if data.get("uuid"):
            value_data["properties"] = json.dumps(dict({"uuid": data["uuid"]}))

        res_data = self.env["of.esb.data"].create(value_data)

        return self.create({"channel": channel, "ttype": ttype.id, "data": res_data.id, "uuid": data.get("uuid")})

    def _handle_bus_rules(self):
        for bus in self:
            # get the rules that are configured on the channel / ttype
            rules = self.env["of.esb.rule"].search(
                [("channel_bus", "in", [bus.channel, False]), ("type_bus", "=", bus.ttype.id)]
            )
            for rule in rules:
                service_exec = rule.service.action_execute_with_delay(args=bus.data)
                data = {
                    "type": "service",
                    "id": rule.service.id,
                    "job": service_exec._uuid,
                    "name": rule.service.name,
                    "uuid": bus.uuid,
                }
                properties = {"uuid": bus.uuid}

                self.send_bus(
                    ttype=self.env.ref("of_esb.type_logs"), channel="history", data=data, properties=properties
                )

    @api.model
    def cron_clean_bus(self):
        delete_date = fields.date.today() - datetime.timedelta(days=7)
        busses = self.search([("create_date", "<", delete_date)])
        busses.unlink()
