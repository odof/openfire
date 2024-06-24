# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from xml.dom import minidom  # nosec B408

from odoo import _, models
from odoo.exceptions import UserError

base_fields = ["create_date", "write_date", "create_uid", "write_uid"]


class ESBService(models.Model):
    _inherit = "of.esb.service"

    def get_data_internal(self, args):
        """
        Fetches data from local Odoo and sends it to the ESB bus.

        Args:
            args (object): An object containing the input data in JSON format. The JSON should have the following
            structure:
                {
                    "in_data": {
                        "data": [
                            {
                                "bus_type": str,
                                "bus_channel": str,
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
            lines = data["data"]
            for line in lines:
                # on vérifie que la table existe bien localement
                if obj := self.env.get(line["model"], False):
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

    def set_data_internal(self, args):
        """
        Processes incoming data and updates or creates records in local Odoo based on the provided data.
        If the table does not exist, the table is created

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
            lines = data["data"]
            for line in lines:
                # on teste l'existence de la table
                if line["model"] in self.env:
                    obj = self.env[line["model"]]
                    results = line["result"]
                elif f"x_{line['model']}" in self.env:
                    obj = self.sudo().update_table(f"x_{line['model']}", line)
                    results = self.convert_fields(line["result"])
                else:
                    obj = self.sudo().create_table(line)
                    results = self.convert_fields(line["result"])
                for result in results:
                    if res_id := result.get("id"):
                        if record := obj.search([("id", "=", res_id)]):
                            record.write(result)
                        else:
                            obj.create(result)
                    else:
                        obj.create(result)
        return []

    def convert_fields(self, results):
        res = []
        for result in results:
            value = {}
            for key in result:
                if key in base_fields:
                    value[key] = result[key]
                else:
                    value[f"x_{key}"] = result[key]
            res.append(value)
        return res

    def create_table(self, line):
        if not line["model"].startswith("x_"):
            model = f"x_{line['model']}"
        else:
            model = line["model"]

        # on crée le modèle
        model_record = self._create_model(model)

        result = line["result"]
        line_fields = list(result[0].keys()) if len(result) > 0 else []
        fields = []
        for field in line_fields:
            if field not in base_fields and not field.startswith("x_"):
                fields.append(f"x_{field}")
            else:
                fields.append(field)

        # on crée les champs ir.model.fields
        self._create_fields(model, model_record, fields)

        # on crée les vues
        self._create_form_view(model, fields)
        self._create_tree_view(model, fields)

        # on crée l'action
        action_record = self._create_action(model)

        # on crée le menu
        self._create_menu(model, action_record)

        # on ajoute les droits
        self._create_access(model, model_record)

        return self.env[model]

    def update_table(self, model, line):
        # on vérifie que le modèle existe bien
        obj_model = self.env["ir.model"].search([("model", "=", model)])
        if not obj_model:
            raise UserError(_("Model does not exit"))

        result = line["result"]
        line_fields = list(result[0].keys()) if len(result) > 0 else []
        fields = []
        for field in line_fields:
            if field not in base_fields and not field.startswith("x_"):
                fields.append(f"x_{field}")
            else:
                fields.append(field)

        # on crée les champs ir.model.fields
        self._create_fields(model, obj_model, fields)

        # on crée les vues form et tree et on les ajoute au modèle
        value_view = self._prepare_form_view_values(model, fields)
        if view_form := self.env["ir.ui.view"].search(
            [
                ("name", "=", f"ESB {model} form"),
                ("model", "=", model),
                ("type", "=", "form"),
            ]
        ):
            view_form.write(value_view)
        else:
            self.env["ir.ui.view"].create(value_view)

        value_view = self._prepare_tree_view_values(model, fields)
        if view_tree := self.env["ir.ui.view"].search(
            [
                ("name", "=", f"ESB {model} tree"),
                ("model", "=", model),
                ("type", "=", "tree"),
            ]
        ):
            view_tree.write(value_view)
        else:
            self.env["ir.ui.view"].create(value_view)

        return self.env[model]

    def _create_model(self, model):
        return self.env["ir.model"].create(
            {
                "name": f"ESB {model}",
                "model": model,
            }
        )

    def _create_fields(self, model, model_record, fields):
        for field in fields:
            if self.env["ir.model.fields"].search_count([("name", "=", field), ("model", "=", model)]) == 0:
                self.env["ir.model.fields"].create(
                    {
                        "name": field,
                        "model": model,
                        "model_id": model_record.id,
                        "field_description": f"{field.replace('x_', '')}",
                        "ttype": "char",
                    }
                )

    def _prepare_form_view_values(self, model, fields):
        root = minidom.Document()  # nosec B408 : We are building an XML document not parsing it
        form = root.createElement("form")
        root.appendChild(form)
        group_xml = root.createElement("group")
        form.appendChild(group_xml)

        for field in fields:
            f_xml = root.createElement("field")
            f_xml.setAttribute("name", field)
            group_xml.appendChild(f_xml)

        arch_db_form = root.toprettyxml(indent="\t")

        return {
            "name": f"ESB {model} form",
            "model": model,
            "type": "form",
            "arch_db": arch_db_form,
        }

    def _prepare_tree_view_values(self, model, fields):
        root = minidom.Document()  # nosec B408 : We are building an XML document not parsing it
        tree = root.createElement("tree")
        root.appendChild(tree)

        for field in fields:
            f_xml = root.createElement("field")
            f_xml.setAttribute("name", field)
            tree.appendChild(f_xml)

        arch_db_tree = root.toprettyxml(indent="\t")
        return {
            "name": f"ESB {model} tree",
            "model": model,
            "type": "tree",
            "arch_db": arch_db_tree,
        }

    def _create_form_view(self, model, fields):
        self.env["ir.ui.view"].create(self._prepare_form_view_values(model, fields))

    def _create_tree_view(self, model, fields):
        self.env["ir.ui.view"].create(self._prepare_tree_view_values(model, fields))

    def _create_action(self, model):
        return self.env["ir.actions.act_window"].create(
            {
                "name": f"Open ESB {model}",
                "res_model": model,
                "view_mode": "tree,form",
            }
        )

    def _create_menu(self, model, action):
        self.env["ir.ui.menu"].create(
            {
                "name": model,
                "parent_id": self.env.ref("of_esb_internal.main_menu_esb_internal").id,
                "action": f"ir.actions.act_window,{action.id}",  # noqa E231
            }
        )

    def _create_access(self, model, model_record):
        self.env["ir.model.access"].create(
            {
                "name": f"Access {model}",
                "model_id": model_record.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }
        )
