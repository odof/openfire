# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


class OFPlanningInterventionTemplate(models.Model):
    _name = 'of.planning.intervention.template'
    _description = "Intervention template"
    _order = 'sequence'

    @api.model
    def _get_default_template_values(self):
        """Helper to combine default values of both templates (sheet and report)."""
        res = self._get_default_template_values_sheet()
        res.update(self._get_default_template_values_report())
        return res

    @api.model
    def _get_default_template_values_sheet(self):
        """Helper to get the default values of the template (sheet)."""
        default_template = self.env.ref(
            'of_planning.of_planning_default_intervention_template', raise_if_not_found=False
        )
        values = {}
        if default_template:
            copy = default_template.copy_data()[0] or {}
            for key, value in copy.items():
                # copier les valeurs du rapport d'intervention
                if isinstance(key, str) and key.startswith("sheet_") and key != 'sheet_use_default':
                    values[key] = value
        return values

    @api.model
    def _get_default_template_values_report(self):
        """Helper to get the default values of the template (report)."""
        default_template = self.env.ref(
            'of_planning.of_planning_default_intervention_template', raise_if_not_found=False
        )
        values = {}
        if default_template:
            copy = default_template.copy_data()[0] or {}
            for key, value in copy.items():
                # copier les valeurs du rapport d'intervention
                if isinstance(key, str) and key.startswith('report_') and key != 'report_use_default':
                    values[key] = value
        return values

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if default_template_values := self._get_default_template_values():
            if isinstance(defaults, dict):  # MJA: default_get renvoie toujours un dict non ?
                defaults.update(default_template_values)
            else:
                defaults = default_template_values
        return defaults

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=1, help="Used to order templates. Lower is better.")
    active = fields.Boolean(default=True)
    code = fields.Char(
        compute='_compute_code',
        inverse='_inverse_code',
        store=True,
        required=True,
    )
    sequence_id = fields.Many2one(comodel_name='ir.sequence', string="Sequence", readonly=True)
    task_id = fields.Many2one(
        comodel_name='of.planning.task', string="Task", help="Task to be carried out during the intervention."
    )
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Fiscal position", company_dependent=True
    )
    line_ids = fields.One2many(
        comodel_name='of.planning.intervention.template.line', inverse_name='template_id', string="Template lines"
    )
    legal = fields.Text(string="Legal notice")
    send_reports = fields.Selection(
        selection=[('manual', "Manual dispatch"), ('auto_done', "Automatic dispatch when the intervention is done")],
        string="Send report",
        default='manual',
        help="* Manual dispatch: manually from the OpenFire web database.\n"
        "* Automatic dispatch at intervention closure: from the mobile app, as soon as the user"
        " clicks on 'Completed' in an intervention, the intervention becomes completed and the intervention"
        " report is automatically e-mailed to the customer.",
    )
    attach_report = fields.Boolean(
        string="Automatic report storage",
        help="The intervention report will be automatically attached to the intervention.",
    )
    is_default_template = fields.Boolean(compute='_compute_is_default_template', store=True)

    # INTERVENTION SHEET
    sheet_use_default = fields.Boolean(
        string="Use default report",
        default=True,
        help="Use the values defined in the default template for the intervention sheet.",
    )
    sheet_title = fields.Char(
        string="Report title", translate=True, help="Define a title for the PDF document of the intervention sheet."
    )
    sheet_partner_id = fields.Boolean(string="Customer", help="Adds address name to document title.")
    sheet_date = fields.Boolean(string="Date", help="Adds intervention date to document title.")

    # Intervention
    sheet_intervention = fields.Boolean(
        string="INTERVENTION", help="Selects or deselects all items to be displayed related to the intervention."
    )
    sheet_intervention_partner_id = fields.Boolean(
        string="Customer", help="Adds the customer to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_partner_code = fields.Boolean(
        string="Customer code", help="Adds the customer code to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_task_id = fields.Boolean(
        string="Task", help="Adds the task to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_task_description = fields.Boolean(
        string="Task description", help="Adds the task description to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_date = fields.Boolean(
        string="Start date", help="Adds the intervention date to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_duration = fields.Boolean(
        string="Duration",
        help="Adds the duration of the intervention in the \"Intervention\" section of the PDF document.",
    )
    sheet_intervention_team_id = fields.Boolean(
        string="Team", help="Adds the selected team to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_employee_ids = fields.Boolean(
        string="Operator(s)", help="Adds technicians to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_company_id = fields.Boolean(
        string="Company", help="Adds the company to the \"Intervention\" section of the PDF document."
    )
    sheet_intervention_label = fields.Boolean(string="Label")
    sheet_intervention_address = fields.Boolean(string="Address")
    sheet_intervention_contact = fields.Boolean(string="Contact")
    sheet_intervention_type = fields.Boolean(string="Intervention type")
    sheet_intervention_description = fields.Boolean(
        string="External description",
        help="Adds the external description to the \"Intervention\" section of the PDF document.",
    )
    sheet_intervention_internal_description = fields.Boolean(
        string="Internal description",
        help="Adds the internal description to the \"Intervention\" section of the PDF document.",
    )

    # History
    sheet_history = fields.Boolean(string="HISTORY", help="Adds customer history to PDF document.")

    # Commande
    sheet_order = fields.Boolean(
        string="ORDER",
        help="Allows you to select or deselect all the items to be displayed linked to"
        " the order associated with the intervention.",
    )
    sheet_order_name = fields.Boolean(
        string="Name", help="Adds the associated order number to the \"Order\" section of the PDF document."
    )
    sheet_order_confirmation_date = fields.Boolean(
        string="Confirmation date",
        help="Adds the associated order confirmation date to the \"Order\" section of the PDF document.",
    )
    sheet_order_user_id = fields.Boolean(
        string="Vendor", help="Adds the seller of the associated order to the \"Order\" section of the PDF document."
    )
    sheet_order_inspection_visit_date = fields.Boolean(
        string="Inspection visit date",
        help="Adds the technical inspection date of the associated order in the \"Order\" section of the PDF document.",
    )
    sheet_order_totals = fields.Boolean(
        string="Totals", help="Adds the associated order total to the \"Order\" section of the PDF document."
    )
    sheet_order_intervention_notes = fields.Boolean(
        string="Intervention notes",
        help="Adds the associated order notes to the \"Order\" section of the PDF document.",
    )

    # Produits et travaux (lignes de commande)
    sheet_products = fields.Boolean(string="PRODUCTS AND WORKS")

    # Livraisons
    sheet_pickings = fields.Boolean(
        string="DELIVERIES", help="Adds delivery notes related to the intervention to the PDF document."
    )

    # Facturation
    sheet_invoicing = fields.Boolean(
        string="INVOICING", help="Adds invoicing for the intervention to the PDF document."
    )

    # Mentions légales
    sheet_legal = fields.Boolean(string="LEGAL NOTICE", help="Adds legal notices to the PDF document.")

    # Compte-Rendu
    sheet_minutes = fields.Boolean(
        string="MINUTES", help="Allows you to select or deselect all elements of the procedure report."
    )
    sheet_minutes_real_dates = fields.Boolean(string="Real dates", help="Adds actual dates of intervention.")
    sheet_minutes_real_duration = fields.Boolean(string="Real duration", help="Adds actual duration of intervention.")
    sheet_minutes_description = fields.Boolean(string="Description", help="Add intervention report.")

    # Photos
    sheet_photos = fields.Boolean(string="PHOTOS", help="Adds photos of the operation to the PDF document.")

    # Signatures
    sheet_signature = fields.Boolean(
        string="SIGNATURES", help="Adds the technician's and customer's signatures to the PDF document."
    )
    sheet_signature_date = fields.Boolean(string="Signature date", help="Adds signature date to PDF document.")

    # Intervention report
    report_use_default = fields.Boolean(
        string="Use default report", default=True, help="Use values set in the default template for the report."
    )
    report_title = fields.Char(
        string="Report title", translate=True, help="Define a title for the PDF document of the intervention report."
    )
    report_partner_id = fields.Boolean(string="Customer", help="Adds the customer's name to the document title.")
    report_date = fields.Boolean(string="Date", help="Adds intervention date to document title.")

    # Intervention
    report_intervention = fields.Boolean(
        string="INTERVENTION", help="Selects or deselects all items to be displayed related to the intervention."
    )
    report_intervention_partner_id = fields.Boolean(
        string="Customer", help="Adds the customer to the \"Intervention\" section of the PDF document."
    )
    report_intervention_partner_code = fields.Boolean(
        string="Customer code", help="Adds the customer code to the \"Intervention\" section of the PDF document."
    )
    report_intervention_task_id = fields.Boolean(
        string="Task", help="Adds the task to the \"Intervention\" section of the PDF document."
    )
    report_intervention_task_description = fields.Boolean(
        string="Task description", help="Adds the task description to the \"Intervention\" section of the PDF document."
    )
    report_intervention_date = fields.Boolean(
        string="Start date", help="Adds the intervention date to the \"Intervention\" section of the PDF document."
    )
    report_intervention_duration = fields.Boolean(
        string="Duration",
        help="Adds the duration of the intervention in the \"Intervention\" section of the PDF document.",
    )
    report_intervention_team_id = fields.Boolean(
        string="Team", help="Adds the selected team to the \"Intervention\" section of the PDF document."
    )
    report_intervention_employee_ids = fields.Boolean(
        string="Operator(s)", help="Adds technicians to the \"Intervention\" section of the PDF document."
    )
    report_intervention_company_id = fields.Boolean(
        string="Company", help="Adds the company to the \"Intervention\" section of the PDF document."
    )
    report_intervention_label = fields.Boolean(string="Label")
    report_intervention_address = fields.Boolean(string="Address")
    report_intervention_contact = fields.Boolean(string="Contact")
    report_intervention_type = fields.Boolean(string="Intervention type")
    report_intervention_description = fields.Boolean(
        string="External description",
        help="Adds the external description to the \"Intervention\" section of the PDF document.",
    )
    report_intervention_internal_description = fields.Boolean(
        string="Internal description",
        help="Adds the internal description to the \"Intervention\" section of the PDF document.",
    )

    # History
    report_history = fields.Boolean(string="HISTORY", help="Adds customer history to PDF document.")

    # Order
    report_order = fields.Boolean(
        string="ORDER",
        help="Allows you to select or deselect all the items to be displayed "
        "linked to the order associated with the intervention.",
    )
    report_order_name = fields.Boolean(
        string="Name", help="Adds the associated order number to the \"Order\" section of the PDF document."
    )
    report_order_confirmation_date = fields.Boolean(
        string="Confirmation date",
        help="Adds the associated order confirmation date to the \"Order\" section of the PDF document.",
    )
    report_order_user_id = fields.Boolean(
        string="Vendor", help="Adds the seller of the associated order to the \"Order\" section of the PDF document."
    )
    report_order_inspection_visit_date = fields.Boolean(
        string="Inspection visit date",
        help="Adds the technical inspection date of the associated order in the \"Order\" section of the PDF document.",
    )
    report_order_totals = fields.Boolean(
        string="Totals", help="Adds the associated order total to the \"Order\" section of the PDF document."
    )
    report_order_intervention_notes = fields.Boolean(
        string="Intervention notes",
        help="Adds the associated order notes to the \"Order\" section of the PDF document.",
    )

    # Produits et travaux (lignes de commande)
    report_products = fields.Boolean(string="PRODUCTS AND WORKS")

    # Deliveries
    report_pickings = fields.Boolean(
        string="DELIVERIES", help="Adds delivery notes related to the intervention to the PDF document."
    )

    # Invoicing
    report_invoicing = fields.Boolean(
        string="INVOICING", help="Adds invoicing for the intervention to the PDF document."
    )

    # Legal notice
    report_legal = fields.Boolean(string="LEGAL NOTICE", help="Adds legal notices to the PDF document.")

    # Intervention's minutes
    report_minutes = fields.Boolean(
        string="MINUTES", help="Allows you to select or deselect all elements of the procedure report"
    )
    report_minutes_real_dates = fields.Boolean(string="Real dates", help="Adds actual dates of intervention.")
    report_minutes_real_duration = fields.Boolean(string="Real duration", help="Adds actual duration of intervention.")
    report_minutes_description = fields.Boolean(string="Description", help="Add intervention report.")

    # Photos
    report_photos = fields.Boolean(string="PHOTOS", help="Adds photos of the operation to the PDF document.")

    # Signatures
    report_signature = fields.Boolean(
        string="SIGNATURES", help="Adds the technician's and customer's signatures to the PDF document."
    )
    report_signature_date = fields.Boolean(string="Signature date", help="Adds signature date to PDF document.")

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends('sheet_use_default')
    def _compute_is_default_template(self):
        for template in self:
            if template == self.env.ref(
                'of_planning.of_planning_default_intervention_template',
                raise_if_not_found=False,
            ):
                template.is_default_template = True

    @api.depends('sequence_id')
    def _compute_code(self):
        for template in self:
            template.code = template.sequence_id.prefix

    def _inverse_code(self):
        sequence_obj = self.env['ir.sequence']
        for template in self:
            if not template.code:
                continue
            sequence_name = f"Modèle d'intervention {template.code}"
            sequence_code = self._name
            # Si une séquence existe déjà avec ce code, on la reprend
            if sequence := sequence_obj.search([('code', '=', sequence_code), ('prefix', '=', self.code)]):
                template.sequence_id = sequence
                continue

            if template.sequence_id and not self.search(
                [('sequence_id', '=', template.sequence_id.id), ('id', '!=', template.id)]
            ):
                # Si la séquence n'est pas utilisée par un autre modèle, on la modifie directement,
                # sinon il faudra en re-créer une.
                template.sequence_id.sudo().write({'prefix': template.code, 'name': sequence_name})
                continue

            # Création d'une séquence pour le modèle
            sequence_data = {
                'name': sequence_name,
                'code': sequence_code,
                'implementation': 'no_gap',
                'prefix': template.code,
                'padding': 4,
            }
            template.sequence_id = self.env['ir.sequence'].sudo().create(sequence_data)

    # --------------------------------------------------------------------------
    # Onchange methods
    # --------------------------------------------------------------------------

    @api.onchange('sheet_use_default')
    def _onchange_sheet_use_default(self):
        if self.sheet_use_default:
            self.update(self._get_default_template_values_sheet())

    @api.onchange('report_use_default')
    def _onchange_report_use_default(self):
        if self.report_use_default:
            self.update(self._get_default_template_values_report())

    @api.onchange('sheet_intervention')
    def _onchange_sheet_intervention(self):
        if self.sheet_intervention:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("sheet_intervention_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('report_intervention')
    def _onchange_report_intervention(self):
        if self.report_intervention:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("report_intervention_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('sheet_order')
    def _onchange_sheet_order(self):
        if self.sheet_order:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("sheet_order_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('report_order')
    def _onchange_report_order(self):
        if self.report_order:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("report_order_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('sheet_minutes')
    def _onchange_sheet_minutes(self):
        if self.sheet_minutes:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("sheet_minutes_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('report_minutes')
    def _onchange_report_minutes(self):
        if self.report_minutes:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("report_minutes_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('sheet_signature')
    def _onchange_sheet_signature(self):
        if self.sheet_signature:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("sheet_signature_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('report_signature')
    def _onchange_report_signature(self):
        if self.report_signature:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("report_signature_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('sheet_photos')
    def _onchange_sheet_photos(self):
        if self.sheet_photos:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("sheet_photos_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    @api.onchange('report_photos')
    def _onchange_report_photos(self):
        if self.report_photos:
            intervention_keys = [key for key in self._fields.keys() if key.startswith("report_photos_")]
            values = {key: True for key in intervention_keys}
            self.update(values)

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model
    def create(self, vals):
        if vals.get('sheet_use_default', False):
            vals.update(self._get_default_template_values_sheet())
        if vals.get('report_use_default', False):
            vals.update(self._get_default_template_values_report())
        return super().create(vals)

    def write(self, vals):
        if vals.get('sheet_use_default', False):
            vals.update(self._get_default_template_values_sheet())
        if vals.get('report_use_default', False):
            vals.update(self._get_default_template_values_report())
        res = super().write(vals)
        default_template = self.env.ref(
            'of_planning.of_planning_default_intervention_template', raise_if_not_found=False
        )
        if default_template and default_template in self:
            others = self.search([('id', '!=', default_template.id), ('sheet_use_default', '=', True)])
            others.write(self._get_default_template_values_sheet())
            others = self.search([('id', '!=', default_template.id), ('report_use_default', '=', True)])
            others.write(self._get_default_template_values_report())
        return res

    def unlink(self):
        default_template = self.env.ref(
            'of_planning.of_planning_default_intervention_template', raise_if_not_found=False
        )
        if default_template and default_template in self and self.env.uid != SUPERUSER_ID:
            raise UserError(_("You cannot unlink the default template"))
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        # We change the name and the code of the template
        default['name'] = self.name + _(" (copy)")
        default['code'] = self.code + _(" (copy)")
        return super().copy(default)
