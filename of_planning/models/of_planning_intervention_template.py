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

    name = fields.Char(required=True)
    sequence = fields.Integer(default=1, help="Used to order templates. Lower is better.")
    active = fields.Boolean(default=True)
    code = fields.Char(compute='_compute_code', inverse='_inverse_code', store=True, required=True)
    sequence_id = fields.Many2one(comodel_name='ir.sequence', string="Sequence", readonly=True)
    task_id = fields.Many2one(comodel_name='of.planning.task', string="Task")
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Fiscal position", company_dependent=True
    )
    line_ids = fields.One2many(
        comodel_name='of.planning.intervention.template.line',
        inverse_name='template_id',
        string="Template lines",
        compute='_compute_template_line',
        store=True,
        readonly=False,
    )
    legal = fields.Text(string="Legal notice")
    send_reports = fields.Selection(
        selection=[('manual', "Manual dispatch"), ('auto_done', "Automatic dispatch when the intervention is done")],
        string="Send report",
        default='manual',
    )
    attach_report = fields.Boolean(
        string="Automatic report storage",
        help="The intervention report will be automatically attached to the intervention.",
    )
    is_default_template = fields.Boolean(compute='_compute_is_default_template', store=True)

    # INTERVENTION SHEET
    sheet_use_default = fields.Boolean(
        string="Use default report", default=True, help="Use values set in the default template for the report."
    )
    sheet_title = fields.Char(string="Report title")
    sheet_partner_id = fields.Boolean(string="Customer")
    sheet_date = fields.Boolean(string="Date")

    # Intervention
    sheet_intervention = fields.Boolean(string="INTERVENTION")
    sheet_intervention_partner_id = fields.Boolean(string="Customer")
    sheet_intervention_partner_code = fields.Boolean(string="Customer code")
    sheet_intervention_task_id = fields.Boolean(string="Task")
    sheet_intervention_task_description = fields.Boolean(string="Task description")
    sheet_intervention_date = fields.Boolean(string="Start date")
    sheet_intervention_duration = fields.Boolean(string="Duration")
    sheet_intervention_team_id = fields.Boolean(string="Team")
    sheet_intervention_employee_ids = fields.Boolean(string="Operator(s)")
    sheet_intervention_company_id = fields.Boolean(string="Company")
    sheet_intervention_label = fields.Boolean(string="Label")
    sheet_intervention_address = fields.Boolean(string="Address")
    sheet_intervention_contact = fields.Boolean(string="Contact")
    sheet_intervention_type = fields.Boolean(string="Intervention type")
    sheet_intervention_description = fields.Boolean(string="External description")
    sheet_intervention_internal_description = fields.Boolean(string="Internal description")

    # History
    sheet_history = fields.Boolean(string="HISTORY")

    # Commande
    sheet_order = fields.Boolean(string="ORDER")
    sheet_order_name = fields.Boolean(string="Name")
    sheet_order_confirmation_date = fields.Boolean(string="Confirmation date")
    sheet_order_user_id = fields.Boolean(string="Vendor")
    sheet_order_inspection_visit_date = fields.Boolean(string="Inspection visit date")
    sheet_order_totals = fields.Boolean(string="Totals")
    sheet_order_intervention_notes = fields.Boolean(string="Intervention notes")

    # Produits et travaux (lignes de commande)
    sheet_products = fields.Boolean(string="PRODUCTS AND WORKS")

    # Livraisons
    sheet_pickings = fields.Boolean(string="DELIVERIES")

    # Facturation
    sheet_invoicing = fields.Boolean(string="INVOICING")

    # Mentions légales
    sheet_legal = fields.Boolean(string="LEGAL NOTICE")

    # Compte-Rendu
    sheet_minutes = fields.Boolean(string="MINUTES")
    sheet_minutes_real_dates = fields.Boolean(string="Real dates")
    sheet_minutes_real_duration = fields.Boolean(string="Real duration")
    sheet_minutes_description = fields.Boolean(string="Description")

    # Photos
    sheet_photos = fields.Boolean(string="PHOTOS")

    # Signatures
    sheet_signature = fields.Boolean(string="SIGNATURES")
    sheet_signature_date = fields.Boolean(string="Signature date")

    # Intervention report
    report_use_default = fields.Boolean(
        string="Use default report", default=True, help="Use values set in the default template for the report."
    )
    report_title = fields.Char(string="Report title")
    report_partner_id = fields.Boolean(string="Customer")
    report_date = fields.Boolean(string="Date")

    # Intervention
    report_intervention = fields.Boolean(string="INTERVENTION")
    report_intervention_partner_id = fields.Boolean(string="Customer")
    report_intervention_partner_code = fields.Boolean(string="Customer code")
    report_intervention_task_id = fields.Boolean(string="Task")
    report_intervention_task_description = fields.Boolean(string="Task description")
    report_intervention_date = fields.Boolean(string="Start date")
    report_intervention_duration = fields.Boolean(string="Duration")
    report_intervention_team_id = fields.Boolean(string="Team")
    report_intervention_employee_ids = fields.Boolean(string="Operator(s)")
    report_intervention_company_id = fields.Boolean(string="Company")
    report_intervention_label = fields.Boolean(string="Label")
    report_intervention_address = fields.Boolean(string="Address")
    report_intervention_contact = fields.Boolean(string="Contact")
    report_intervention_type = fields.Boolean(string="Intervention type")
    report_intervention_description = fields.Boolean(string="External description")
    report_intervention_internal_description = fields.Boolean(string="Internal description")

    # History
    report_history = fields.Boolean(string="HISTORY")

    # Order
    report_order = fields.Boolean(string="ORDER")
    report_order_name = fields.Boolean(string="Name")
    report_order_confirmation_date = fields.Boolean(string="Confirmation date")
    report_order_user_id = fields.Boolean(string="Vendor")
    report_order_inspection_visit_date = fields.Boolean(string="Inspection visit date")
    report_order_totals = fields.Boolean(string="Totals")
    report_order_intervention_notes = fields.Boolean(string="Intervention notes")

    # Produits et travaux (lignes de commande)
    report_products = fields.Boolean(string="PRODUCTS AND WORKS")

    # Deliveries
    report_pickings = fields.Boolean(string="DELIVERIES")

    # Invoicing
    report_invoicing = fields.Boolean(string="INVOICING")

    # Legal notice
    report_legal = fields.Boolean(string="LEGAL NOTICE")

    # Intervention's minutes
    report_minutes = fields.Boolean(string="MINUTES")
    report_minutes_real_dates = fields.Boolean(string="Real dates")
    report_minutes_real_duration = fields.Boolean(string="Real duration")
    report_minutes_description = fields.Boolean(string="Description")

    # Photos
    report_photos = fields.Boolean(string="PHOTOS")

    # Signatures
    report_signature = fields.Boolean(string="SIGNATURES")
    report_signature_date = fields.Boolean(string="Signature date")

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

    @api.depends('task_id')
    def _compute_fiscal_position(self):
        for template in self:
            if template.task_id and template.task_id.fiscal_position_id and not template.fiscal_position_id:
                template.fiscal_position_id = template.task_id.fiscal_position_id

    @api.depends('task_id')
    def _compute_template_line(self):
        for template in self:
            if template.task_id and template.task_id.product_id:
                template.line_ids |= self.env['of.planning.intervention.template.line'].new(
                    {
                        'template_id': template.id,
                        'product_id': template.task_id.product_id.id,
                        'qty': 1,
                        'price_unit': template.task_id.product_id.lst_price,
                        'name': template.task_id.product_id.name,  # FIXME: not the same as _compute_name in line model
                    }
                )

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
