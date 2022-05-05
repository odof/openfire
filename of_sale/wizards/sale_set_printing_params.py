# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class OFSaleWizardSetPrintingParams(models.TransientModel):
    _name = 'of.sale.wizard.set.printing.params'

    # Address
    pdf_hide_global_address_label = fields.Boolean(
        string="(OF) Description of the delivery and invoicing address", default=False,
        help='Hide the "Delivery and billing address" label in the PDF quote report ?')
    pdf_adresse_civilite = fields.Boolean(
        string="(OF) Titles", default=False,
        help="Display titles in PDF reports ?")
    pdf_adresse_nom_parent = fields.Boolean(
        string="(OF) Contact parent name", default=False,
        help="Show contact 'parent' name instead of contact name in PDF reports ?"
    )
    pdf_adresse_telephone = fields.Selection(
        [
            (1, "Display in the main address insert"),
            (2, "Display in an additional information badge"),
            (3, "Display in the main address insert and in an additional information badge")
        ], string="(OF) Telephone",
        help="Where to display the phone number in PDF reports ? Do not put anything so as not to display."
    )
    pdf_adresse_mobile = fields.Selection(
        [
            (1, "Display in the main address insert"),
            (2, "Display in an additional information badge"),
            (3, "Display in the main address insert and in an additional information badge")
        ], string="(OF) Mobile",
        help="Where to display the mobile phone number in PDF reports? Do not put anything so as not to display."
    )
    pdf_adresse_fax = fields.Selection(
        [
            (1, "Display in the main address insert"),
            (2, "Display in an additional information badge"),
            (3, "Display in the main address insert and in an additional information badge")
        ], string="(OF) Fax",
        help="Where to display the fax number in PDF reports? Do not put anything so as not to display."
    )
    pdf_adresse_email = fields.Selection(
        [
            (1, "Display in the main address insert"),
            (2, "Display in an additional information badge"),
            (3, "Display in the main address insert and in an additional information badge")
        ], string="(OF) E-mail",
        help="Where to display the email address in PDF reports? Do not put anything so as not to display."
    )
    # Labels
    pdf_masquer_pastille_payment_term = fields.Boolean(
        string="(OF) Hide payment terms badge", default=False,
        help="Hide payment terms badge in PDF reports ?"
    )
    pdf_vt_pastille = fields.Boolean(
        string="(OF) Date VT badge", default=False,
        help="Display the technical visit date in a badge in the PDF quotes report ?"
    )
    pdf_date_validite_devis = fields.Boolean(
        string="(OF) Quote validity date", default=False,
        help="Show the validity date in the PDF quote report ?"
    )
    pdf_masquer_pastille_commercial = fields.Boolean(
        string="(OF) Hide commercial badge", default=False,
        help="Hide the sales badge in PDF reports ?"
    )
    pdf_mail_commercial = fields.Boolean(
        string="(OF) Sales email", default=False,
        help="Display the email in the commercial button of the PDF reports ?"
    )
    # Layout category
    of_color_bg_section = fields.Char(
        string="(OF) Background color",
        help="Choose a background color for the section titles", default="#F0F0F0"
    )
    of_color_font = fields.Char(
        string="(OF) Font color",
        help="Choose a color for the section headings", default="#000000"
    )
    # Order lines
    pdf_display_product_ref_setting = fields.Boolean(
        string="(OF) Products Ref.", default=False,
        help="Show product references in PDF reports ?"
    )
    # Other
    pdf_afficher_multi_echeances = fields.Boolean(
        string="(OF) Multi-maturities", default=False,
        help="Show multiple due dates in PDF reports ?"
    )
    of_pdf_taxes_display = fields.Boolean(
        string="(OF) Tax details", help="Show tax detail table in PDF reports")

    @api.model
    def default_get(self, fields_list):
        res = super(OFSaleWizardSetPrintingParams, self).default_get(fields_list)

        IrValues = self.env['ir.values']
        defaults = {}
        ir_values_dict = IrValues.get_defaults_dict('sale.config.settings')
        for name in fields_list:
            if name in ir_values_dict:
                defaults[name] = ir_values_dict[name]
                continue
        defaults = self._convert_to_write(defaults)
        res.update(defaults)
        return res

    @api.multi
    def set_pdf_hide_global_address_label_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_hide_global_address_label', self.pdf_hide_global_address_label)

    @api.multi
    def set_pdf_adresse_civilite_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_civilite', self.pdf_adresse_civilite)

    @api.multi
    def set_pdf_adresse_nom_parent_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_nom_parent', self.pdf_adresse_nom_parent)

    @api.multi
    def set_pdf_adresse_telephone_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_telephone', self.pdf_adresse_telephone)

    @api.multi
    def set_pdf_adresse_mobile_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_mobile', self.pdf_adresse_mobile)

    @api.multi
    def set_pdf_adresse_fax_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_fax', self.pdf_adresse_fax)

    @api.multi
    def set_pdf_adresse_email_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_email', self.pdf_adresse_email)

    @api.multi
    def set_pdf_masquer_pastille_payment_term(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_masquer_pastille_payment_term', self.pdf_masquer_pastille_payment_term)

    @api.multi
    def set_pdf_vt_pastille_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_vt_pastille', self.pdf_vt_pastille)

    @api.multi
    def set_pdf_date_validite_devis_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_date_validite_devis', self.pdf_date_validite_devis)

    @api.multi
    def set_pdf_masquer_pastille_commercial(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_masquer_pastille_commercial', self.pdf_masquer_pastille_commercial)

    @api.multi
    def set_pdf_mail_commercial_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_mail_commercial', self.pdf_mail_commercial)

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_color_bg_section', self.of_color_bg_section)

    @api.multi
    def set_of_color_font_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_color_font', self.of_color_font)

    @api.multi
    def set_pdf_display_product_ref_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_display_product_ref_setting', self.pdf_display_product_ref_setting)

    @api.multi
    def set_pdf_afficher_multi_echeances_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_afficher_multi_echeances', self.pdf_afficher_multi_echeances)

    @api.multi
    def set_of_pdf_taxes_display(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_pdf_taxes_display', self.of_pdf_taxes_display)

    @api.multi
    def action_validate(self):
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)()
