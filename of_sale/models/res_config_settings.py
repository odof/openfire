# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Sale settings
    of_deposit_product_categ_id = fields.Many2one(
        comodel_name='product.category',
        string="(OF) Down payment product category",
        help="Category of items used for down payments",
        config_parameter='of.sale.of_deposit_product_categ_id',
    )
    module_of_order_line_option = fields.Boolean(string="(OF) Order line option")
    of_fiscal_position_required = fields.Boolean(
        string="(OF) Fiscal position", config_parameter='of.sale.of_fiscal_position_required'
    )
    of_allow_quote_addition = fields.Boolean(
        string="(OF) Additional quotes", config_parameter='of.sale.of_allow_quote_addition'
    )
    of_stop_payment_term_propagation = fields.Boolean(
        string="(OF) Stop payment term propagation",
        help="Allow to stop the propagation of the payment term from the sale order to the invoice",
        config_parameter='of.sale.of_stop_payment_term_propagation',
    )
    group_of_display_tax_inclued_total_in_so_lines = fields.Boolean(
        string="Display subtotals taxes incl. per order line",
        help="Displays the subtotals including VAT per order line. Only in the form and not in the reports.",
        implied_group='of_sale.of_group_display_tax_inclued_total_in_so_lines',
    )
    group_of_display_tax_exclued_total_in_so_lines = fields.Boolean(
        string="Display subtotals taxes excl. per order line",
        help="Displays the subtotals excluding VAT per order line. Only in the form and not in the reports.",
        implied_group='of_sale.of_group_display_tax_exclued_total_in_so_lines',
    )
    of_grouped_invoicing = fields.Selection(
        selection=[
            ('default_grouping', "Grouping by company, partner, currency (default mode)"),
            ('sale_order', "Grouping by sale order"),
        ],
        string="(OF) Grouped invoicing",
        config_parameter='of.sale.of_grouped_invoicing',
        default='default_grouping',
    )
    of_sale_mail_subtype_subscription = fields.Boolean(
        string="(OF) Enable subscription of subtype E-Mail for sale orders",
        help="Only the recipients and subscribers to this document subtype will receive the emails.",
        config_parameter='of.sale.of_sale_mail_subtype_subscription',
    )
    of_sale_confirmation_date_mode = fields.Selection(
        selection=[('default', "Automatic (default)"), ('manual', "Manual")],
        string="(OF) Mode of confirmation date on Sales",
        config_parameter='of.sale.of_sale_confirmation_date_mode',
        default='default',
    )
    of_copy_opportunity_with_sale_order = fields.Boolean(
        string="(OF) Copy opportunity",
        config_parameter='of.sale.of_copy_opportunity_with_sale_order',
    )

    # Invoice settings
    of_color_bg_section = fields.Char(
        string="Background color of section headings",
        help="Choose a background color for the section headings",
        default="#f0f0f0",
        config_parameter='of.sale.report.account.move.of_color_bg_section',
    )
    of_color_font_section = fields.Char(
        string="Font color of section headings",
        help="Choose a font color for the section headings",
        default='#000000',
        config_parameter='of.sale.report.account.move.of_color_font',
    )
    of_validate_pickings_on_move = fields.Selection(
        [
            ('no', "Do not manage delivery notes from the invoice"),
            ('manage', "Manage delivery notes after invoice validation"),
            ('validate', "Validate delivery notes at the time of invoice validation"),
        ],
        string="(OF) Delivery notes management in Customer Invoice",
        default='no',
        required=True,
        config_parameter='of.sale.of_validate_pickings_on_move',
    )

    # UX fields (not computed, not stored) to display warnings
    show_warning_b2b_to_b2c = fields.Boolean(string="Has B2B/B2C field changed (from b2b to b2c)", store=False)
    show_warning_b2c_to_b2b = fields.Boolean(string="Has B2B/B2C field changed (from b2c to b2b)", store=False)

    def _set_of_validate_pickings_on_move(self):
        view = self.env.ref('of_sale.of_sale_account_move_delivery_notes_view_form', raise_if_not_found=False)
        active = self.of_validate_pickings_on_move in ('manage', 'validate')
        view and view.write({'active': active})

    def _set_of_fiscal_position_required(self):
        view = self.env.ref('of_sale.of_sale_order_form_fiscal_position_required', raise_if_not_found=False)
        view and view.write({'active': self.of_fiscal_position_required})

    def _set_of_sale_mail_subtype_subscription(self):
        subtype = self.env.ref('of_sale.mt_of_sale_mail_subscription', raise_if_not_found=False)
        subtype and subtype.write({'hidden': not self.of_sale_mail_subtype_subscription})

    def _set_of_sale_confirmation_date_mode(self):
        view = self.env.ref('of_sale.of_sale_view_confirmation_date_order_form', raise_if_not_found=False)
        active = self.of_sale_confirmation_date_mode == 'manual'
        view and view.write({'active': active})

    def set_values(self):
        super().set_values()
        self._set_of_validate_pickings_on_move()
        self._set_of_fiscal_position_required()
        self._set_of_sale_mail_subtype_subscription()
        self._set_of_sale_confirmation_date_mode()

    @api.onchange('group_of_display_tax_inclued_total_in_so_lines', 'group_of_display_tax_exclued_total_in_so_lines')
    def _onchange_group_of_display_tax_inclued_total_in_so_lines(self):
        original_show_line_subtotals_tax_selection = (
            self.env['ir.config_parameter'].sudo().get_param('account.show_line_subtotals_tax_selection')
        )
        if (
            self.group_of_display_tax_exclued_total_in_so_lines
            and self.group_of_display_tax_inclued_total_in_so_lines
            or not (
                self.group_of_display_tax_exclued_total_in_so_lines
                or self.group_of_display_tax_inclued_total_in_so_lines
            )
        ):
            self.show_warning_b2c_to_b2b = False
            self.show_warning_b2b_to_b2c = False
            if self.show_line_subtotals_tax_selection != original_show_line_subtotals_tax_selection:
                self.show_line_subtotals_tax_selection = original_show_line_subtotals_tax_selection
        elif (
            self.group_of_display_tax_inclued_total_in_so_lines
            and self.show_line_subtotals_tax_selection != 'tax_included'
        ):
            self.show_line_subtotals_tax_selection = 'tax_included'
            self.show_warning_b2b_to_b2c = True
            self.show_warning_b2c_to_b2b = False
        elif (
            self.group_of_display_tax_exclued_total_in_so_lines
            and self.show_line_subtotals_tax_selection != 'tax_excluded'
        ):
            self.show_line_subtotals_tax_selection = 'tax_excluded'
            self.show_warning_b2c_to_b2b = True
            self.show_warning_b2b_to_b2c = False
        else:
            self.show_warning_b2c_to_b2b = False
            self.show_warning_b2b_to_b2c = False

    @api.onchange('show_line_subtotals_tax_selection')
    def _onchange_show_line_subtotals_tax_selection(self):
        if (
            self.show_line_subtotals_tax_selection == 'tax_included'
            and not self.group_of_display_tax_inclued_total_in_so_lines
            and self.group_of_display_tax_exclued_total_in_so_lines
        ):
            self.group_of_display_tax_inclued_total_in_so_lines = True
            self.group_of_display_tax_exclued_total_in_so_lines = False
        elif (
            self.show_line_subtotals_tax_selection == 'tax_excluded'
            and not self.group_of_display_tax_exclued_total_in_so_lines
            and self.group_of_display_tax_inclued_total_in_so_lines
        ):
            self.group_of_display_tax_inclued_total_in_so_lines = False
            self.group_of_display_tax_exclued_total_in_so_lines = True
