# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import api, models


class ESBService(models.Model):
    _inherit = "of.esb.service"

    def get_data_odoo(self, args):
        """
        Fetches data from Odoo based on the provided arguments and sends it to the ESB bus.

        Args:
            args (object): An object containing the input data in JSON format. The JSON should have the following
            structure:
                {
                    "in_data": {
                        "data": [
                            {
                                "bus_type": str,
                                "bus_channel": str,
                                "connection_id": int,
                                "data": [
                                    {
                                        "model": str,
                                        "domain": list,
                                        "offset": int,
                                        "limit": int,
                                        "fields": list
                                    }
                                ]
                            }
                        ],
                        "uuid": str
                    }
                }

        Returns:
            bool: Always returns list. Needed because `_get_data*` method to return a list.
        """
        data_list = json.loads(args.in_data)["data"]
        uuid = json.loads(args.in_data)["uuid"]
        for data in data_list:
            bus_type = data["bus_type"]
            bus_channel = data["bus_channel"]
            if connection := self.env["of.esb.connection"].search([("id", "=", data["connection_id"])], limit=1):
                odoo_base = connection.connect()
                lines = data["data"]
                for line in lines:
                    obj = odoo_base.env[line["model"]]
                    if connection.odoo_company_id:
                        obj = obj.with_context(allowed_company_ids=[connection.odoo_company_id])
                    line["result"] = obj.search_read(
                        domain=line.get("domain", []),
                        offset=line.get("offset", 0),
                        limit=line.get("limit", 0),
                        fields=line["fields"],
                    )
                data["uuid"] = uuid

                ttype = self.env["of.esb.type.bus"].search([("name", "=", bus_type)], limit=1)

                self.env["of.esb.bus"].send_bus(ttype=ttype, channel=bus_channel, data=data, properties={"uuid": uuid})
        return []

    def set_data_odoo(self, args):
        """
        Processes incoming data and updates or creates records in Odoo based on the provided data.

        Args:
            args (object): An object containing the input data in JSON format. The JSON should have a key 'in_data'
                which contains another JSON object with a key 'data'. This 'data' key should map to a list
                of dictionaries, each representing a connection and its associated data.

        Returns:
            bool: Always returns list. Needed because `_set_data*` method to return a list.

        The expected structure of the input JSON is:
        {
            "in_data": {
                "data": [
                    {
                        "connection_id": int,
                        "data": [
                            {
                                "model": str,
                                "result": [
                                    {
                                        "id": int (optional),
                                        ... (other fields to update or create)
                                    },
                                    ...
                                ]
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        }
        """
        for data in json.loads(args.in_data)["data"]:
            if connection := self.env["of.esb.connection"].search([("id", "=", data["connection_id"])], limit=1):
                odoo_base = connection.connect()
                lines = data["data"]
                for line in lines:
                    obj = odoo_base.env[line["model"]]
                    if connection.odoo_company_id:
                        obj = obj.with_context(allowed_company_ids=[connection.odoo_company_id])
                    results = line["result"]
                    for result in results:
                        if res_id := result.get("id"):
                            if record := obj.search([("id", "=", res_id)]):
                                record.write(result)
                            else:
                                obj.create(result)
                        else:
                            obj.create(result)
        return []

    @api.model
    def preview_odoo(self, connection, lines):
        """
        Preview Odoo records based on the provided connection and lines.

        This method connects to an Odoo instance using the provided connection,
        iterates over the given lines, and performs a `search_read` operation on
        each line's specified model. The results are then added to the line's
        'result' key.

        Args:
            connection (object): The connection object to connect to Odoo.
            lines (list): A list of dictionaries, where each dictionary contains:
                - 'model' (str): The name of the Odoo model to query.
                - 'domain' (list, optional): The domain filter for the search.
                - 'offset' (int, optional): The offset for the search.
                - 'limit' (int, optional): The limit for the search.
                - 'fields' (list): The list of fields to retrieve.

        Returns:
            str: A JSON-formatted string containing the results of the search_read
                operations for each line.
        """
        if connection:
            odoo_base = connection.connect()
            for line in lines:
                obj = odoo_base.env[line["model"]]
                if connection.odoo_company_id:
                    obj = obj.with_context(allowed_company_ids=[connection.odoo_company_id])
                line["result"] = obj.search_read(
                    domain=line.get("domain", []),
                    offset=line.get("offset", 0),
                    limit=line.get("limit", 0),
                    fields=line["fields"],
                )
        return json.dumps(lines, indent=2)
