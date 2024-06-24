# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one


class ESBHistory(models.Model):
    _name = "of.esb.history"
    _description = "ESB History"
    _rec_name = "ttype"

    ttype = fields.Char(string="Type")
    uuid = fields.Char()
    date = fields.Datetime()
    history = fields.Text()
    user = fields.Many2one(comodel_name="res.users")
    mermaid = fields.Text(compute="_compute_mermaid")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    def _compute_mermaid(self):
        """
        Computes a Mermaid.js diagram representation of the history of events.

        This method processes the history of events stored in the record and generates
        a Mermaid.js diagram that visually represents the sequence of triggers, services,
        and jobs. The diagram is stored in the `mermaid` field of the record.

        The method defines two helper functions:
        - `get_trigger(user, lines)`: Extracts the trigger event from the history lines.
        - `get_services(trigger, lines)`: Constructs the Mermaid.js representation of services
            and jobs based on the trigger and history lines.

        For each record:
        - If the history is empty, sets the `mermaid` field to a default "graph LR;".
        - Otherwise, constructs the Mermaid.js diagram by combining the trigger and services
            representations and sets it to the `mermaid` field.
        """

        def get_trigger(user, lines):
            trigger = False
            for line in lines:
                if line["type"] == "trigger":
                    trigger = line
                    break
            return f"""{trigger['slug']}-- {user} -->""" if trigger else ""

        def get_services(trigger, lines):
            mermaid = ""
            services = {}
            jobs = {}

            for line in lines:
                if line["type"] == "service":
                    services[line["job_id"]] = line
                if line["type"] == "job":
                    jobs[line["name"]] = line

            for service in services:
                mermaid_service = (
                    f"""{trigger}{services[service]['slug']}"""
                    f"""subgraph \"Service: {services[service]['name']} (durée : """
                    f"""{jobs[services[service]['job_id']]['exec_time']} secondes)\""""
                    f"""{services[service]['slug']} --> {jobs[services[service]['job_id']]['name']} end"""
                    f"""{jobs[services[service]['job_id']]['name']} -.-> """
                    f"""{jobs[services[service]['job_id']]['state']}"""
                )
                mermaid += mermaid_service
            return mermaid

        for record in self:
            if len(record.history) == 0:
                record.mermaid = "graph LR;"
            else:
                mermaid = "graph LR; Trigger --> "
                lines = json.loads(record.history)
                trigger = get_trigger(record.user.display_name, lines)
                services = get_services(trigger, lines)
                mermaid = f"""{mermaid}
                {services}
                """
                record.mermaid = mermaid

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @api.model
    def cron_history_build(self):
        self.build_history()

    @api.model
    def build_history(self):
        """
        Builds and updates the history of logs grouped by data UUID.

        Raises:
            json.JSONDecodeError: If there is an error decoding JSON data from the log properties or in_data.
        """
        # Groups the logs by data uuid
        lines = self.env["of.esb.bus"].search(
            [("channel", "=", "history"), ("ttype", "=", self.env.ref("of_esb.type_logs").id)]
        )
        history_lines = {}
        for line in lines:
            properties = json.loads(line.data.properties)
            if data_uuid := properties.get("uuid"):
                if data_uuid in history_lines:
                    history_lines[data_uuid]["history"] += line
                else:
                    history_lines[data_uuid] = {"history": line}

        # Builds the history
        for uuid in history_lines:
            res = []
            user_id = False
            lines_data = history_lines[uuid]["history"].mapped("data")
            for line_data in lines_data:
                in_data = json.loads(line_data.in_data)
                if ttype := in_data.get("type", False):
                    if ttype == "trigger":
                        user_id = in_data.get("user_id")
                        res.append(
                            {
                                "date": str(line_data.create_date),
                                "type": "trigger",
                                "name": in_data.get("name", ""),
                                "state": "",
                                "slug": slugify_one(in_data.get("name", "")),
                            }
                        )
                    if ttype == "service":
                        res.append(
                            {
                                "date": str(line_data.create_date),
                                "type": "service",
                                "name": in_data.get("name", ""),
                                "state": "",
                                "job_id": in_data.get("job"),
                                "slug": slugify_one(in_data.get("name", "")),
                            }
                        )
                        job = self.env["queue.job"].search([("uuid", "=", in_data.get("job"))])
                        res.append(
                            {
                                "date": str(job.date_started),
                                "type": "job",
                                "name": in_data.get("job"),
                                "state": job.state,
                                "exec_time": job.exec_time,
                            }
                        )
            if len(lines_data) > 0:
                value = {
                    "ttype": "trigger",
                    "uuid": uuid,
                    "date": lines_data[0].create_date,
                    "user": user_id,
                    "history": json.dumps(res),
                }
                history = self.search([("uuid", "=", uuid)])
                if len(history):
                    history.write(value)
                else:
                    self.create(value)
