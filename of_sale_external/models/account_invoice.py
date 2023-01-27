# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_report_template_id = fields.Many2one(
        comodel_name='of.report.template', string=u"Report template",
        domain="[('model','in',['account.invoice', False])]")

    def pdf_afficher_nom_parent(self):
        return self.of_report_template_id.pdf_address_contact_parent_name if self.of_report_template_id else super(
            AccountInvoice, self).pdf_afficher_nom_parent()

    def pdf_afficher_civilite(self):
        return self.of_report_template_id.pdf_address_contact_titles if self.of_report_template_id else super(
            AccountInvoice, self).pdf_afficher_civilite()

    def pdf_afficher_telephone(self):
        return self.of_report_template_id.pdf_address_contact_phone if self.of_report_template_id else super(
            AccountInvoice, self).pdf_afficher_telephone()

    def pdf_afficher_mobile(self):
        return self.of_report_template_id.pdf_address_contact_mobile if self.of_report_template_id else super(
            AccountInvoice, self).pdf_afficher_mobile()

    def pdf_afficher_fax(self):
        return self.of_report_template_id.pdf_address_contact_fax if self.of_report_template_id else super(
            AccountInvoice, self).pdf_afficher_fax()

    def pdf_afficher_email(self):
        return self.of_report_template_id.pdf_address_contact_email if self.of_report_template_id else super(
            AccountInvoice, self).pdf_afficher_email()

    def pdf_mention_legale(self):
        return self.of_report_template_id.pdf_legal_notice if self.of_report_template_id else super(
            AccountInvoice, self).pdf_mention_legale()

    def pdf_masquer_commercial(self):
        return (not self.of_report_template_id.pdf_commercial_insert) if self.of_report_template_id else super(
            AccountInvoice, self).pdf_masquer_commercial()

    def pdf_vt_pastille(self):
        return self.of_report_template_id.pdf_technical_visit_insert if self.of_report_template_id else super(
            AccountInvoice, self).pdf_vt_pastille()

    def get_color_section(self):
        return self.of_report_template_id.pdf_section_bg_color if self.of_report_template_id else super(
            AccountInvoice, self).get_color_section()

    def get_color_font(self):
        return self.of_report_template_id.pdf_section_font_color if self.of_report_template_id else super(
            AccountInvoice, self).get_color_font()


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def of_get_line_name(self):
        self.ensure_one()
        if self.invoice_id.of_report_template_id:
            # inhiber l'affichage de la référence
            afficher_ref = self.invoice_id.of_report_template_id.pdf_product_reference
            le_self = self.with_context(
                lang=self.invoice_id.partner_id.lang,
                partner=self.invoice_id.partner_id.id,
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
            return super(AccountInvoiceLine, self).of_get_line_name()
