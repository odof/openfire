# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class OFReportTemplate(models.Model):
    _name = 'of.report.template'
    _description = u"Modèle d'impression"
    _order = 'name'

    active = fields.Boolean(string=u"Active", default=True)
    name = fields.Char(string=u"Name", required=True)
    model = fields.Selection(
        selection=[('sale.order', u"Devis"), ('account.invoice', u"Facture")], string=u"Model")

    # Address insert
    pdf_address_title = fields.Boolean(
        string="Address title", default=True,
        help="If checked, displays the label \"Delivery and billing address\"")
    pdf_address_contact_titles = fields.Boolean(
        string="Titles", help="If checked, displays the titles in the address insert")
    pdf_address_contact_parent_name = fields.Boolean(
        string="Contact's parent name",
        help="If checked, displays the contact's parent name in the address insert")
    pdf_address_contact_name = fields.Boolean(
        string="Contact's name", default=True,
        help="If checked, displays the contact's name in the address insert")
    pdf_address_contact_phone = fields.Boolean(
        string="Phone (contact)", default=True,
        help="If checked, displays the contact's phone in the address insert")
    pdf_address_contact_mobile = fields.Boolean(
        string="Mobile (contact)", default=True,
        help="If checked, displays the contact's mobile in the address insert")
    pdf_address_contact_fax = fields.Boolean(
        string="Fax (contact)",
        help="If checked, displays the contact's fax in the address insert")
    pdf_address_contact_email = fields.Boolean(
        string="Email (contact)", default=True,
        help="If checked, displays the contact's mail in the address insert")
    pdf_shipping_address_specific_title = fields.Char(string="Shipping Address Title", size=30)

    # Commercial insert
    pdf_commercial_insert = fields.Boolean(
        string="Commercial insert", help="If checked, displays the commercial insert")
    pdf_commercial_contact = fields.Boolean(
        string="Contact", default=True, help="If checked, displays the contact in the commercial insert")
    pdf_commercial_email = fields.Boolean(
        string="Email (commercial)", help="If checked, displays the email in the commercial insert")

    pdf_sale_show_tax = fields.Selection(selection=[
        ('subtotal', u"Show line subtotals without taxes (B2B)"),
        ('total', u"Show line subtotals with taxes included (B2C)"),
        ('both', u"Show line subtotals without taxes (B2B) and with taxes included (B2C)")],
        default='subtotal', required=True, string=u"Tax Display")

    # Customers insert
    pdf_customer_insert = fields.Boolean(
        string="Customers insert", default=True, help="If checked, displays the customers insert")
    pdf_customer_phone = fields.Boolean(
        string="Phone (customer)", default=True,
        help="If checked, displays the customer's phone in the customers insert")
    pdf_customer_mobile = fields.Boolean(
        string="Mobile (customer)", default=True,
        help="If checked, displays the customer's mobile in the customers insert")
    pdf_customer_fax = fields.Boolean(
        string="Fax (customer)", default=True,
        help="If checked, displays the customer's fax in the customers insert")
    pdf_customer_email = fields.Boolean(
        string="Email (customer)", default=True,
        help="If checked, displays the customer's email in the customers insert")

    # Inserts
    pdf_payment_term_insert = fields.Boolean(
        string="Payment terms", default=True, help="If checked, displays the payment terms in the inserts")
    pdf_customer_ref_insert = fields.Boolean(
        string="Customer reference", default=True, help="If checked, displays the customer reference in the inserts")
    pdf_technical_visit_insert = fields.Boolean(
        string="Date of technical visit",
        help="If checked, displays the technical visit date in the inserts")
    pdf_validity_insert = fields.Boolean(
        string="Validity date",
        help="If checked, displays the validity date in the inserts")
    pdf_display_incoterm = fields.Boolean(
        string="Incoterms",
        help="If checked, the printed reports will display the incoterms for the sales orders and the related invoices")

    # Sections
    pdf_section_bg_color = fields.Char(
        string="Background color", default="#FFFFFF",
        help="Background color of the section headings. Default is white.")
    pdf_section_font_color = fields.Char(
        string="Font color", default="#000000",
        help="Font color of the section headings. Default is black.")

    # Order lines
    pdf_product_reference = fields.Boolean(
        string="Product reference",
        help="If checked, displays the product reference in the order lines on the report")

    # Other
    pdf_payment_schedule = fields.Boolean(
        string="Payment schedule",
        help="If checked, displays the Payment schedule in the report")
    pdf_taxes_detail = fields.Boolean(
        string="Taxes detail", help="If checked, displays the taxes detail in the report")

    # Signatures insert
    pdf_signatures_insert = fields.Boolean(
        string="Signatures", help="If checked, displays signatures insert in PDF reports")
    pdf_customer_signature = fields.Boolean(
        string="Customer signature",
        help="If checked, displays the customer signature insert at the bottom left of the quotation")
    pdf_vendor_signature = fields.Boolean(
        string="Salesman signature",
        help="If checked, displays the salesman signature insert at the bottom right of the quotation")
    pdf_signature_text = fields.Char(
        string="Signature statement",
        help="Signature comment positioned below the titles \"Salesman signature\" and \"Customer signature\"")

    pdf_legal_notice = fields.Text(
        string=u"Legal notice", help=u"Will be displayed un the bottom comment")

    # Utilisé que lorsque of_sale_order_dates est installé
    pdf_requested_week = fields.Boolean(string="Requested week")

    @api.multi
    def toggle_active(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """
        for record in self:
            record.active = not record.active

    @api.multi
    def write(self, vals):
        if vals.get('model') == 'sale.order':
            self.env['account.invoice'].search([('of_report_template_id', 'in', self.ids)]).write(
                {'of_report_template_id': False})
        elif vals.get('model') == 'account.invoice':
            self.env['sale.order'].search([('of_report_template_id', 'in', self.ids)]).write(
                {'of_report_template_id': False})
        return super(OFReportTemplate, self).write(vals)
