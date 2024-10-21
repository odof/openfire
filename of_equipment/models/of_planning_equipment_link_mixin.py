# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class OFPlanningInterventionLinkMixin(models.AbstractModel):
    _name = "of.planning.equipment.link.mixin"
    _description = "Mixin for equipment link between equipment and Intervention/Service request"
    _rec_name = "equipment_id"

    sequence = fields.Integer(default=10)
    equipment_report_tmpl_id = fields.Many2one(
        comodel_name="of.equipment.intervention.report.template", string="Equipment report"
    )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer")
    address_id = fields.Many2one(comodel_name="res.partner", string="Address")
    equipment_ids_domain = fields.Many2many(
        comodel_name="of.equipment",
        compute="_compute_equipment_ids_domain",
        help="Technical field to compute domain for equipment_id based on partner and address",
    )
    equipment_id = fields.Many2one(
        comodel_name="of.equipment",
        string="Equipment",
        domain="[('id', 'in', equipment_ids_domain and equipment_ids_domain or [])]",
        required=True,
    )
    equipment_address = fields.Char(compute="_compute_equipment_address", string="Equipment address")
    task_id = fields.Many2one(
        comodel_name="of.planning.task", string="Task", compute="_compute_task_id", store=True, readonly=False
    )
    task_duration = fields.Float(related="task_id.duration", string="Duration", help="Task duration in hours")
    task_description = fields.Text(related="task_id.description", string="Task Description")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("partner_id", "address_id")
    def _compute_equipment_ids_domain(self):
        for link in self:
            domain = []
            if link.partner_id and link.address_id:
                domain = [
                    "|",
                    ("customer_id", "=", link.partner_id.id),
                    "|",
                    ("customer_id", "=", link.address_id.id),
                    ("site_address_id", "=", link.address_id.id),
                ]
            elif link.partner_id:
                domain = [("customer_id", "=", link.partner_id.id)]
            elif link.address_id:
                domain = [
                    "|",
                    ("customer_id", "=", link.address_id.id),
                    ("site_address_id", "=", link.address_id.id),
                ]

            link.equipment_ids_domain = self.env["of.equipment"].search(domain).ids if domain else []

    @api.depends("equipment_id")
    def _compute_equipment_address(self):
        link_with_address = self.filtered(lambda r: r.equipment_id.site_address_id)
        for record in link_with_address:
            address = record.equipment_id.site_address_id
            city = address.city
            address_parts = [address.street2, address.street, address.zip, city and city.upper() or ""]
            record.equipment_address = ", ".join(part for part in address_parts if part)
        for record in self - link_with_address:
            record.equipment_address = False

    @api.depends("equipment_report_tmpl_id")
    def _compute_task_id(self):
        for record in self:
            record.task_id = record.equipment_report_tmpl_id.task_id

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _add_missing_mixin_link_fields(self, inverse_field_key=False, template_field=False, vals_list=None):
        """Add required missing fields like report template and task to the equipment link mixin values if they are not
        present."""
        if not inverse_field_key and not template_field and not vals_list:
            return

        for vals in vals_list:
            equipment_report_tmpl = False
            if vals.get("equipment_report_tmpl_id"):
                equipment_report_tmpl = self.env["of.equipment.intervention.report.template"].browse(
                    vals["equipment_report_tmpl_id"]
                )
            elif vals.get(inverse_field_key):
                parent_model = self._fields[inverse_field_key].comodel_name
                parent_record = self.env[parent_model].browse(vals[inverse_field_key])
                equipment_report_tmpl = getattr(parent_record, template_field).default_equipment_report_tmpl_id
                vals["equipment_report_tmpl_id"] = equipment_report_tmpl.id or False
            if equipment_report_tmpl and not vals.get("task_id"):
                vals["task_id"] = equipment_report_tmpl.task_id.id or False

    def _get_changes_message_post(self, old_values, new_values):
        """
        Generates an HTML formatted message indicating the changes between old and new values of fields.

        Args:
            old_values (dict): A dictionary containing the old values of the fields.
            new_values (dict): A dictionary containing the new values of the fields.

        Returns:
            str: An HTML string representing the changes in a list format, where each list item shows the old value,
                    an arrow icon, and the new value.

        Raises:
            ValidationError: If the method is called on multiple records.
        """
        self.ensure_one()
        data = {}
        for field in new_values.keys():
            field_type = self._fields[field].type
            comodel_name = self._fields[field].comodel_name if field_type == "many2one" else None
            if field_type == "many2one":
                nameget_old = self.env[comodel_name].browse(old_values[field]).name_get()
                nameget_new = self.env[comodel_name].browse(new_values[field]).name_get()
                old_value = nameget_old[0][1] if isinstance(nameget_old, list) and nameget_old else old_values[field]
                new_value = nameget_new[0][1] if isinstance(nameget_new, list) and nameget_new else new_values[field]
            else:
                old_value = old_values[field]
                new_value = new_values[field]
            data[field] = {
                "old_value": old_value,
                "new_value": new_value,
            }

        arrow = _(
            "<i class='o_TrackingValue_separator fa fa-long-arrow-right mx-1 text-600' title='Changed' role='img' "
            "aria-label='Changed'/>"
        )
        empty_str = _("Empty")
        return (
            "<ul>"
            + "".join(
                f"<li>{data[field]['old_value'] or empty_str} {arrow} {data[field]['new_value'] or empty_str}</li>"
                for field in data
            )
            + "</ul>"
        )
