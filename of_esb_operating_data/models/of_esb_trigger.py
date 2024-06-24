# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one


class ESBTrigger(models.Model):
    _inherit = "of.esb.trigger"

    is_operating_data = fields.Boolean()
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("create_auto_esb"):
            self._pre_process_trigger_create(vals_list)
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------

    def _pre_process_trigger_create(self, vals_list):
        """
        Pre-processes the creation of triggers by automatically creating associated extracts, loads, transforms,
        services, and rules based on the provided values.

        Args:
            vals_list (list): A list of dictionaries containing the values for the triggers to be created.

        Notes:
            - If 'is_operating_data' is present in the context or in the values, it forces the creation of an extract,
                load, and transform linked to the trigger.
            - For each trigger, a service and a rule are created to react to the trigger.
        """
        for vals in vals_list:
            if self.env.context.get("default_is_operating_data", False) or vals.get("is_operating_data", False):
                # Extract
                extract = self.env["of.esb.extract"].create(
                    {
                        "name": vals.get("name"),
                        "partner_id": vals.get("partner_id"),
                        "uuid": vals.get("uuid"),
                    }
                )

                # Service
                service = self.env["of.esb.service"].create(
                    {
                        "name": f"Extract : {vals.get('name')}",
                        "code": f"""# on appelle la fonction extract
self.env['of.esb.extract'].browse({extract.id}).execute(args)
""",  # noqa
                        "ttype": "user",
                        "uuid": vals.get("uuid"),
                    }
                )

                # Rule
                self.env["of.esb.rule"].create(
                    {
                        "name": f"Trigger : {vals.get('name')}",
                        "ttype": "user",
                        "channel_bus": slugify_one(vals.get("name")),
                        "type_bus": self.env.ref("of_esb.type_webhook").id,
                        "service": service.id,
                        "uuid": vals.get("uuid"),
                    }
                )
