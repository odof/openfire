# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def _auto_init(self):
        """
        Certain paramètres d'affichage sont passés de Booléen à Sélection.
        Cette fonction est appelée à chaque mise à jour mais ne fait quelque chose que la première fois qu'elle est appelée.
        """
        set_value = False
        # Cette fonction n'a encore jamais été appelée
        if not self.env['ir.values'].get_default('sale.config.settings', 'bool_vers_selection_fait'):
            set_value = True
        super(OFSaleConfiguration, self)._auto_init()
        if set_value:
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_telephone'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_telephone', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_telephone', 0)
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_mobile'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_mobile', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_mobile', 0)
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_fax'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_fax', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_fax', 0)
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_email'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_email', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_email', 0)
            if not self.env['ir.values'].get_default('sale.config.settings', 'of_color_font'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_color_font', "#000000")
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'bool_vers_selection_fait', True)

    of_deposit_product_categ_id_setting = fields.Many2one(
        'product.category',
        string=u"(OF) Catégorie des acomptes",
        help=u"Catégorie des articles utilisés pour les acomptes"
    )

    stock_warning_setting = fields.Boolean(
        string="(OF) Stock", required=True, default=False,
        help=u"Afficher les messages d'avertissement de stock ?"
    )

    pdf_display_product_ref_setting = fields.Boolean(
        string=u"(OF) Réf. produits", required=True, default=False,
        help=u"Afficher les références produits dans les rapports PDF ?"
    )

    pdf_date_validite_devis = fields.Boolean(
        string=u"(OF) Date validité devis", required=True, default=False,
        help=u"Afficher la date de validité dans le rapport PDF des devis ?"
    )

    pdf_vt_pastille = fields.Boolean(
        string=u"(OF) Date VT pastille", required=True, default=False,
        help=u"Afficher la date de visite technique dans une pastille dans le rapport PDF des devis ?"
    )

    pdf_hide_global_address_label = fields.Boolean(
        string=u"(OF) Libellé adresse de livraison et facturation", required=True, default=False,
        help=u'Masquer le libellé "Adresse de livraison et de facturation" dans le rapport PDF des devis ?')

    pdf_masquer_pastille_commercial = fields.Boolean(
        string=u"(OF) Masquer pastille commercial", required=True, default=False,
        help=u"Masquer la pastille commercial dans les rapports PDF ?"
    )

    pdf_mail_commercial = fields.Boolean(
        string=u"(OF) pastille commercial", required=True, default=False,
        help=u"Afficher l'email dans la pastille commercial des rapports PDF ?"
    )

    pdf_masquer_pastille_payment_term = fields.Boolean(
        string=u"(OF) Masquer pastille conditions de règlement", required=True, default=False,
        help=u"Masquer la pastille conditions de règlement dans les rapports PDF ?"
    )

    pdf_adresse_nom_parent = fields.Boolean(
        string=u"(OF) Nom parent contact", required=True, default=False,
        help=u"Afficher le nom du 'parent' du contact au lieu du nom du contact dans les rapport PDF ?"
    )
    pdf_adresse_civilite = fields.Boolean(
        string=u"(OF) Civilités", required=True, default=False,
        help=u"Afficher la civilité dans les rapport PDF ?"
    )
    pdf_adresse_telephone = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Téléphone",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_adresse_mobile = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Mobile",
        help=u"Où afficher le numéro de téléphone mobile dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_adresse_fax = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) Fax",
        help=u"Où afficher le fax dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_adresse_email = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) E-mail",
        help=u"Où afficher l'adresse email dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_afficher_multi_echeances = fields.Boolean(
        string=u"(OF) Multi-échéances", required=True, default=False,
        help=u"Afficher les échéances multiples dans les rapports PDF ?"
    )
    of_color_bg_section = fields.Char(
        string="(OF) Couleur fond titres section",
        help=u"Choisissez un couleur de fond pour les titres de section", default="#F0F0F0"
    )
    of_color_font = fields.Char(
        string="(OF) Couleur police titre section",
        help=u"Choisissez un couleur pour les titres de section", default="#000000"
    )

    of_position_fiscale = fields.Boolean(string="(OF) Position fiscale")
    of_allow_quote_addition = fields.Boolean(string=u"(OF) Devis complémentaires")

    group_of_order_line_option = fields.Boolean(
        string=u"(OF) Options de ligne de commande", implied_group='of_sale.group_of_order_line_option',
        group='base.group_portal,base.group_user,base.group_public')

    of_invoice_grouped = fields.Selection(selection=[
        (0, 'Groupement par partenaire + devise'),
        (1, 'Groupement par commande'),
        ], string=u"(OF) Facturation groupée")

    @api.multi
    def set_pdf_adresse_nom_parent_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_nom_parent', self.pdf_adresse_nom_parent)

    @api.multi
    def set_pdf_adresse_civilite_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_civilite', self.pdf_adresse_civilite)

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
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'stock_warning_setting', self.stock_warning_setting)

    @api.multi
    def set_pdf_display_product_ref_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_display_product_ref_setting', self.pdf_display_product_ref_setting)

    @api.multi
    def set_pdf_date_validite_devis_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_date_validite_devis', self.pdf_date_validite_devis)

    @api.multi
    def set_pdf_vt_pastille_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_vt_pastille', self.pdf_vt_pastille)

    @api.multi
    def set_pdf_hide_global_address_label_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_hide_global_address_label', self.pdf_hide_global_address_label)

    @api.multi
    def set_pdf_masquer_pastille_commercial(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_masquer_pastille_commercial', self.pdf_masquer_pastille_commercial)

    @api.multi
    def set_pdf_mail_commercial_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_mail_commercial', self.pdf_mail_commercial)

    @api.multi
    def set_pdf_masquer_pastille_payment_term(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_masquer_pastille_payment_term', self.pdf_masquer_pastille_payment_term)

    @api.multi
    def set_of_deposit_product_categ_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_deposit_product_categ_id_setting', self.of_deposit_product_categ_id_setting.id)

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_color_bg_section', self.of_color_bg_section)

    @api.multi
    def set_of_color_font_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_color_font', self.of_color_font)

    @api.multi
    def set_pdf_afficher_multi_echeances_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_afficher_multi_echeances', self.pdf_afficher_multi_echeances)

    @api.multi
    def set_of_position_fiscale(self):
        view = self.env.ref('of_sale.of_sale_order_form_fiscal_position_required')
        if view:
            view.write({'active': self.of_position_fiscale})
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_position_fiscale',
            self.of_position_fiscale)

    @api.multi
    def set_of_allow_quote_addition_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_allow_quote_addition', self.of_allow_quote_addition)

    @api.multi
    def set_of_invoice_grouped_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_invoice_grouped', self.of_invoice_grouped)
