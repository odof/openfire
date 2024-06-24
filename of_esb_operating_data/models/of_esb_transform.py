# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.http_routing.models.ir_http import slugify_one

logger = logging.getLogger(__name__)


class ESBTransform(models.Model):
    _name = "of.esb.transform"
    _description = "ESB Transform"

    def _default_code(self):
        return """
# Vous retrouvez dans la variable data, toutes les données qui viennent de l'étape précédente
# Vous devez retourner dans la variable result, tout ce qui ira dans l'étape suivante"""

    name = fields.Char()
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    code = fields.Text(required=True, default=lambda r: r._default_code())
    load_id = fields.Many2one(comodel_name="of.esb.load", string="Load")
    uuid = fields.Char(default=lambda r: uuid.uuid4())
    example = fields.Text(compute="_compute_example")
    preview = fields.Text()

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("load_id")
    def _compute_example(self):
        for record in self:
            if record.load_id and record.load_id.connection_id:
                record.example = record.load_id.connection_id.get_out_example()
            else:
                record.example = "#TODO"

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, list_vals):
        esb_transforms = super().create(list_vals)
        if self.env.context.get("create_auto_esb"):
            esb_transforms._process_transform_create()  # On crée un service et une règle pour chaque transform
        return esb_transforms

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_button_preview(self):
        """Display the preview of the transform
        Raises:
            UserError: If the extract line is of type 'code'
        """
        # il faut retrouver l'extract juste avant le transform
        extract_line = self.env["of.esb.extract.line"].search([("transform_id", "=", self.id)], limit=1)
        if extract_line.type_data == "code":
            raise UserError(_("You can not see preview with an extract line of type 'code'"))
        self.preview = self.env["of.esb.service"].preview(extract_line.connection_id, json.loads(extract_line.data))

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------

    def execute(self, args):
        for record in self:
            properties = json.loads(args.properties)
            result = {}
            exec(  # nosec B102
                record.code,
                {"data": json.loads(args.in_data), "env": self.env, "logger": logger, "self": record, "json": json},
                result,
            )
            # on ne garde dans result que ce qui est contenu dans la variable result
            data = {"data": result.get("result", {}), "uuid": properties.get("uuid")}
            self.env["of.esb.bus"].send_bus(
                ttype=self.env.ref("of_esb_operating_data.type_load"),
                channel=slugify_one(record.load_id.name),
                data=data,
                properties={"uuid": properties.get("uuid")},
            )

    def _process_transform_create(self):
        """
        Creates a new service and rule for each record in the current set.
        """
        for record in self:
            if record.load_id:
                load = record.load_id
            else:
                # Load
                load = self.env["of.esb.load"].create(
                    {
                        "name": f"Load {record.name}",
                        "partner_id": record.partner_id.id,
                        "uuid": record.uuid,
                    }
                )
                record.load_id = load.id

            service = self.env["of.esb.service"].create(
                {
                    "name": f"Load : {record.load_id.name}",
                    "code": f"""# on appelle la fonction load
self.env['of.esb.load'].browse({load.id}).execute(args)
""",  # noqa
                    "ttype": "user",
                    "uuid": record.load_id.uuid,
                }
            )

            self.env["of.esb.rule"].create(
                {
                    "name": f"Transform : {record.load_id.name}",
                    "ttype": "user",
                    "channel_bus": slugify_one(record.load_id.name),
                    "type_bus": self.env.ref("of_esb_operating_data.type_load").id,
                    "service": service.id,
                    "uuid": record.load_id.uuid,
                }
            )
