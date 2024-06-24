# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, fields, models

type_simple = ["boolean", "float", "monetary", "char", "html", "selection", "integer", "date", "datetime", "text"]
type_related = [
    "many2one",
]
type_list = ["one2many", "many2many"]


class Base(models.AbstractModel):
    _inherit = "base"

    def convert_parser(self, parser, name=None):
        """Convertit le parser en dict.

        On convertit le parser qui est sous forme de liste (plus facile à écrire pour un humain)
        en parser sous forme de dict, plus facile à parcourir pour une machine :)
        """
        if type(parser) is dict:
            return parser

        res = {}
        for key in parser:
            if type(key) is tuple:
                res[key[0]] = self.convert_parser(key[1], key[0])
            else:
                res[key] = ""
        return res

    def action_export_json(self, parser=None):
        if not parser:
            parser = []

        parser = self.convert_parser(parser)

        ir_model_data_obj = self.env["ir.model.data"]
        res = []
        for record in self:
            value = {}

            # on va chercher si on a un xml_id pour ce record
            xml_id = ir_model_data_obj.search(
                [
                    ("name", "=", f"{record._name.replace('.', '_')}_{record.id}"),
                    ("module", "=", record._original_module),
                    ("model", "=", record._name),
                    ("res_id", "=", record.id),
                ]
            )
            if not xml_id:
                xml_id = ir_model_data_obj.create(
                    {
                        "name": f"{record._name.replace('.', '_')}_{record.id}",
                        "module": record._original_module,
                        "model": record._name,
                        "res_id": record.id,
                        "noupdate": True,
                    }
                )

            value["xml_id"] = xml_id.complete_name
            fields_get = record.fields_get()
            for field in fields_get:
                name = fields_get[field].get("name")
                if name in parser:
                    ttype = fields_get[field]["type"]
                    if ttype in type_simple:
                        if ttype == "date":
                            if not record[name]:
                                json_value = None
                            else:
                                json_value = fields.Date.to_date(record[name]).isoformat()
                        elif ttype == "datetime":
                            if not record[name]:
                                json_value = None
                            else:
                                json_value = fields.Datetime.to_datetime(record[name]).isoformat()
                        else:
                            json_value = record[name]
                        if not json_value and ttype != "boolean":
                            json_value = None
                        value[name] = json_value
                    elif ttype in type_related:
                        value[name] = record[name].action_export_json(parser.get(name))
                    elif ttype in type_list:
                        lines = []
                        for line in record[name]:
                            lines.append(line.action_export_json(parser.get(name)))
                        value[name] = lines
            res.append(value)
        if len(res) == 1:
            res = res[0]
        return res

    def action_import_json(self, data, parser=None):
        res = []
        if not parser:
            parser = {}

        if not data:
            data = []
        if type(data) is dict:
            data = [data]

        ir_model_data_obj = self.env["ir.model.data"]
        ir_model_field_obj = self.env["ir.model.fields"]

        parser = self.convert_parser(parser)
        for line in data:
            value = {}
            xml_id = False
            line_xml_id = line.get("xml_id")
            module = line_xml_id.split(".")[0]
            obj_name = line_xml_id.split(".")[1]

            xml_id = ir_model_data_obj.search(
                [
                    ("module", "=", module),
                    ("name", "=", obj_name),
                ],
                limit=1,
            )

            for name in parser:
                if name in line:
                    # en fonction du type de champs, on va l'enregistrer de façon différente
                    field = ir_model_field_obj.search([("model", "=", self._name), ("name", "=", name)], limit=1)

                    if not field:
                        continue

                    if field.ttype in type_simple:
                        value[name] = line[name]
                    elif field.ttype in type_related:
                        res_imp = self.env[field.relation].action_import_json(line[name], parser[name])
                        if x_id := res_imp.get("xml_id"):
                            record = self.env[field.relation].browse(x_id.res_id)
                            record.write(res_imp.get("value"))
                        else:
                            record = self.env[field.relation].create(res_imp.get("value"))
                            # on crée le xml_id pour une prochaine mise à jour
                            ir_model_data_obj.create(
                                {
                                    "name": res_imp.get("name"),
                                    "module": res_imp.get("module"),
                                    "model": record._name,
                                    "res_id": record.id,
                                    "noupdate": True,
                                }
                            )
                        value[name] = record.id
                    elif field.ttype in type_list:
                        lines = []
                        for li in line[name]:
                            res_imp = self.env[field.relation].action_import_json(li, parser[name])
                            if x_id := res_imp.get("xml_id"):
                                record = self.env[field.relation].browse(x_id.res_id)
                                record.write(res_imp.get("value"))
                            else:
                                record = self.env[field.relation].create(res_imp.get("value"))
                                # on crée le xml_id pour une prochaine mise à jour
                                ir_model_data_obj.create(
                                    {
                                        "name": res_imp.get("name"),
                                        "module": res_imp.get("module"),
                                        "model": record._name,
                                        "res_id": record.id,
                                        "noupdate": True,
                                    }
                                )
                            lines += record.ids
                        value[name] = [Command.set(lines)]
            res.append({"value": value, "xml_id": xml_id, "name": obj_name, "module": module})
        if len(res) == 1:
            res = res[0]
        return res
