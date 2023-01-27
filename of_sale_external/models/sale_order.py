# -*- coding: utf-8 -*-
# License AGPL-3.0 if self.of_report_template_id else later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_specific_title = fields.Char(string=u"Titre spécifique", size=45)
    of_specific_date = fields.Date(string=u"Date spécifique")
    of_report_template_id = fields.Many2one(
        comodel_name='of.report.template', string=u"Report template", domain="[('model','in',['sale.order', False])]")

    def pdf_pdf_sale_show_tax(self):
        # L'affichage des prix HT/TTC était géré par groupe, mais on ne peut pas récupérer
        # ce mode de fonctionnement avec les modes d'impression
        return self.of_report_template_id.pdf_sale_show_tax if self.of_report_template_id else False

    def pdf_payment_schedule(self):
        return self.of_report_template_id.pdf_payment_schedule if self.of_report_template_id else super(
            SaleOrder, self).pdf_payment_schedule()

    def pdf_address_contact_parent_name(self):
        return self.of_report_template_id.pdf_address_contact_parent_name if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_contact_parent_name()

    def pdf_address_contact_titles(self):
        return self.of_report_template_id.pdf_address_contact_titles if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_contact_titles()

    def pdf_address_contact_name(self):
        return self.of_report_template_id.pdf_address_contact_name if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_contact_name()

    def pdf_address_contact_phone(self):
        return self.of_report_template_id.pdf_address_contact_phone if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_contact_phone()

    def pdf_address_contact_mobile(self):
        return self.of_report_template_id.pdf_address_contact_mobile if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_contact_mobile()

    def pdf_address_contact_fax(self):
        return self.of_report_template_id.pdf_address_contact_fax if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_contact_fax()

    def pdf_address_contact_email(self):
        return self.of_report_template_id.pdf_address_contact_email if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_contact_email()

    def pdf_technical_visit_insert(self):
        return self.of_report_template_id.pdf_technical_visit_insert if self.of_report_template_id else super(
            SaleOrder, self).pdf_technical_visit_insert()

    def pdf_validity_insert(self):
        return self.of_report_template_id.pdf_validity_insert if self.of_report_template_id else super(
            SaleOrder, self).pdf_validity_insert()

    def pdf_address_title(self):
        return self.of_report_template_id.pdf_address_title if self.of_report_template_id else super(
            SaleOrder, self).pdf_address_title()

    def pdf_shipping_address_specific_title(self):
        return self.of_report_template_id.pdf_shipping_address_specific_title \
            if self.of_report_template_id and self.of_report_template_id.pdf_shipping_address_specific_title \
            else super(SaleOrder, self).pdf_shipping_address_specific_title()

    def pdf_commercial_insert(self):
        return self.of_report_template_id.pdf_commercial_insert if self.of_report_template_id else super(
            SaleOrder, self).pdf_commercial_insert()

    def pdf_commercial_contact(self):
        return self.of_report_template_id.pdf_commercial_contact if self.of_report_template_id else super(
            SaleOrder, self).pdf_commercial_contact()

    def pdf_commercial_email(self):
        return self.of_report_template_id.pdf_commercial_email if self.of_report_template_id else super(
            SaleOrder, self).pdf_commercial_email()

    def pdf_customer_insert(self):
        return self.of_report_template_id.pdf_customer_insert if self.of_report_template_id else super(
            SaleOrder, self).pdf_customer_insert()

    def pdf_customer_phone(self):
        return self.of_report_template_id.pdf_customer_phone if self.of_report_template_id else super(
            SaleOrder, self).pdf_customer_phone()

    def pdf_customer_mobile(self):
        return self.of_report_template_id.pdf_customer_mobile if self.of_report_template_id else super(
            SaleOrder, self).pdf_customer_mobile()

    def pdf_customer_fax(self):
        return self.of_report_template_id.pdf_customer_fax if self.of_report_template_id else super(
            SaleOrder, self).pdf_customer_fax()

    def pdf_customer_email(self):
        return self.of_report_template_id.pdf_customer_email if self.of_report_template_id else super(
            SaleOrder, self).pdf_customer_email()

    def pdf_payment_term_insert(self):
        return self.of_report_template_id.pdf_payment_term_insert if self.of_report_template_id else super(
            SaleOrder, self).pdf_payment_term_insert()

    def pdf_customer_ref_insert(self):
        return self.of_report_template_id.pdf_customer_ref_insert if self.of_report_template_id else super(
            SaleOrder, self).pdf_customer_ref_insert()

    def pdf_taxes_detail(self):
        return self.of_report_template_id.pdf_taxes_detail if self.of_report_template_id else super(
            SaleOrder, self).pdf_taxes_detail()

    def pdf_signatures_insert(self):
        return self.of_report_template_id.pdf_signatures_insert if self.of_report_template_id else super(
            SaleOrder, self).pdf_signatures_insert()

    def pdf_vendor_signature(self):
        return self.of_report_template_id.pdf_vendor_signature if self.of_report_template_id else super(
            SaleOrder, self).pdf_vendor_signature()

    def pdf_customer_signature(self):
        return self.of_report_template_id.pdf_customer_signature if self.of_report_template_id else super(
            SaleOrder, self).pdf_customer_signature()

    def pdf_signature_text(self):
        return self.of_report_template_id.pdf_signature_text if self.of_report_template_id else super(
            SaleOrder, self).pdf_signature_text()

    def get_color_section(self):
        return self.of_report_template_id.pdf_section_bg_color if self.of_report_template_id else super(
            SaleOrder, self).get_color_section()

    def get_color_font(self):
        return self.of_report_template_id.pdf_section_font_color if self.of_report_template_id else super(
            SaleOrder, self).get_color_font()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def of_get_line_name(self):
        self.ensure_one()
        if self.order_id.of_report_template_id:
            # inhiber l'affichage de la référence
            afficher_ref = self.order_id.of_report_template_id.pdf_product_reference
            le_self = self.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
            )
            name = le_self.name
            if not afficher_ref:
                if name.startswith("["):
                    splitted = name.split("]")
                    if len(splitted) > 1:
                        splitted.pop(0)
                        name = ']'.join(splitted).strip()
            return name.split("\n")
        else:
            return super(SaleOrderLine, self).of_get_line_name()
