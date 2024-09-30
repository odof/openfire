# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models


class OFCreateEquipmentWizard(models.TransientModel):
    _name = "of.create.equipment.wizard"
    _description = "Create Equipment Wizard from a Sale Order or an Invoice"

    @api.model
    def _get_domain_product(self):
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        product_ids = []
        if not active_id or not active_model:
            return product_ids
        if active_model == "sale.order":
            record_lines = self.env[active_model].browse(active_id).order_line
            product_ids = record_lines.mapped("product_id").ids
        elif active_model == "account.move":
            record_lines = self.env[active_model].browse(active_id).invoice_line_ids
            product_ids = record_lines.mapped("product_id").ids
        return [("id", "in", product_ids)]

    @api.model
    def _get_customer_id_default(self):
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        if active_id and active_model in ("sale.order", "account.move"):
            return self.env[active_model].browse(active_id).partner_id
        return

    @api.model
    def _get_reseller_installer_id_default(self):
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        if active_id and active_model in ("sale.order", "account.move"):
            return self.env[active_model].browse(active_id).company_id.partner_id
        return

    @api.model
    def _get_service_date_default(self):
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        if active_id and active_model:
            record = self.env[active_model].browse(active_id)
            if active_model == "sale.order":
                return record.date_order
            elif active_model == "account.move":
                return record.invoice_date
        return

    @api.model
    def _get_domain_site(self):
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        if active_id and active_model:
            partner = self.env[active_model].browse(active_id).partner_id
            return [("id", "child_of", partner.id)]
        return []

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        context = self._context
        result.setdefault("res_model", context.get("active_model"))
        result.setdefault("res_id", context.get("active_id"))
        return result

    name = fields.Char(string="Serial Number")
    product_id = fields.Many2one(comodel_name="product.product", string="Equipment", domain=_get_domain_product)
    customer_id = fields.Many2one(comodel_name="res.partner", string="Customer", default=_get_customer_id_default)
    site_address_id = fields.Many2one(comodel_name="res.partner", string="Installation Site", domain=_get_domain_site)
    reseller_id = fields.Many2one(
        comodel_name="res.partner", string="Reseller", default=_get_reseller_installer_id_default
    )
    installer_id = fields.Many2one(
        comodel_name="res.partner", string="Installer", default=_get_reseller_installer_id_default
    )
    service_date = fields.Date(default=_get_service_date_default)
    res_id = fields.Integer(string="Model ID")
    res_model = fields.Char(string="Model")

    def action_button_create_equipment(self):
        return self.action_create_equipment()

    def action_create_equipment(self):
        return self.env["of.equipment"].create(self._get_equipment_values())

    def action_button_create_and_display_equipment(self):
        return {
            "name": _("Equipment"),
            "view_type": "form",
            "view_mode": "form",
            "view_id": self.env.ref("of_equipment.of_equipment_view_form").id,
            "res_model": "of.equipment",
            "type": "ir.actions.act_window",
            "res_id": self.action_create_equipment().id,
            "context": self._context,
        }

    def _get_equipment_values(self):
        return {
            "name": self.name or False,
            "product_id": self.product_id.id if self.product_id else False,
            "customer_id": self.customer_id.id if self.customer_id else False,
            "site_address_id": self.site_address_id.id if self.site_address_id else False,
            "reseller_id": self.reseller_id.id if self.reseller_id else False,
            "installer_id": self.installer_id.id if self.installer_id else False,
            "service_date": self.service_date or False,
            "order_ids": [Command.link(self.res_id)] if self.res_model == "sale.order" else [],
            "invoice_ids": [Command.link(self.res_id)] if self.res_model == "account.move" else [],
        }
