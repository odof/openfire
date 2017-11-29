# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def pdf_afficher_nom_parent(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_nom_parent')

    def pdf_afficher_civilite(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_civilite')

    def pdf_afficher_telephone(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_telephone')

    def pdf_afficher_mobile(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_mobile')

    def pdf_afficher_fax(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_fax')

    def pdf_afficher_email(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_email')

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def of_get_line_name(self):
        self.ensure_one()
        # inhiber l'affichage de la référence
        afficher_ref = self.env['ir.values'].get_default('account.config.settings', 'pdf_display_product_ref')
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
                    name = ''.join(splitted)
        return name.split("\n")  # utilisation t-foreach dans template qweb


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    pdf_adresse_nom_parent = fields.Boolean(string=u"(OF) Nom parent contact", required=True, default=False,
            help=u"Afficher le nom du 'parent' du contact au lieu du nom du contact dans les rapport PDF ?")
    pdf_adresse_civilite = fields.Boolean(string=u"(OF) Civilités", required=True, default=False,
            help=u"Afficher la civilité dans les rapport PDF ?")
    pdf_adresse_telephone = fields.Boolean(string=u"(OF) Téléphone", required=True, default=False,
            help=u"Afficher le numéro de téléphone dans les rapport PDF ?")
    pdf_adresse_mobile = fields.Boolean(string=u"(OF) Mobile", required=True, default=False,
            help=u"Afficher le numéro de téléphone mobile dans les rapport PDF ?")
    pdf_adresse_fax = fields.Boolean(string="(OF) Fax", required=True, default=False,
            help=u"Afficher le fax dans les rapport PDF ?")
    pdf_adresse_email = fields.Boolean(string="(OF) E-mail", required=True, default=False,
            help=u"Afficher l'adresse email dans les rapport PDF ?")
    pdf_display_product_ref = fields.Boolean(string="(OF) Réf. produits", required=True, default=False,
            help="Afficher les références produits dans les rapports PDF ?")

    @api.multi
    def set_pdf_adresse_nom_parent_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_nom_parent', self.pdf_adresse_nom_parent)

    @api.multi
    def set_pdf_adresse_civilite_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_civilite', self.pdf_adresse_civilite)

    @api.multi
    def set_pdf_adresse_telephone_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_telephone', self.pdf_adresse_telephone)

    @api.multi
    def set_pdf_adresse_mobile_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_mobile', self.pdf_adresse_mobile)

    @api.multi
    def set_pdf_adresse_fax_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_fax', self.pdf_adresse_fax)

    @api.multi
    def set_pdf_adresse_email_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_email', self.pdf_adresse_email)

    @api.multi
    def set_pdf_display_product_ref_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_display_product_ref', self.pdf_display_product_ref)
