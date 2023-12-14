# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    @api.model
    def _auto_init(self):
        """
        Certain paramètres d'affichage sont passés de Booléen à Sélection.
        Cette fonction est appelée à chaque mise à jour mais ne fait quelque chose qu'à la première mise à jour.
        """
        set_value = False
        # Cette fonction n'a encore jamais été appelée
        if not self.env['ir.values'].get_default('account.config.settings', 'bool_vers_selection_fait'):
            set_value = True
        super(AccountConfigSettings, self)._auto_init()
        if set_value:
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_telephone'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_telephone', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_telephone', 0)
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_mobile'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_mobile', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_mobile', 0)
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_fax'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_fax', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_fax', 0)
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_email'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_email', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_email', 0)
            self.env['ir.values'].sudo().set_default('account.config.settings', 'bool_vers_selection_fait', True)

    pdf_adresse_nom_parent = fields.Boolean(
        string=u"(OF) Nom parent contact", required=True, default=False,
        help=u"Afficher le nom du 'parent' du contact au lieu du nom du contact dans les rapport PDF ?")
    pdf_adresse_civilite = fields.Boolean(
        string=u"(OF) Civilités", required=True, default=False,
        help=u"Afficher la civilité dans les rapport PDF ?")
    pdf_adresse_telephone = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Téléphone",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_mobile = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Mobile",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_fax = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) Fax",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_email = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) E-mail",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_display_product_ref = fields.Boolean(
        string="(OF) Réf. produits", required=True, default=False,
        help="Afficher les références produits dans les rapports PDF ?")

    pdf_mention_legale = fields.Text(
        string=u"(OF) Mentions légales", help=u"Sera affiché dans les factures sous les commentaires du bas"
    )
    pdf_masquer_pastille_commercial = fields.Boolean(
        string=u"(OF) Masquer pastille commercial", required=True, default=False,
        help=u"Masquer la pastille commercial dans les rapports PDF ?"
    )

    @api.multi
    def set_pdf_adresse_nom_parent_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_adresse_nom_parent', self.pdf_adresse_nom_parent
        )

    @api.multi
    def set_pdf_adresse_civilite_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_adresse_civilite', self.pdf_adresse_civilite
        )

    @api.multi
    def set_pdf_adresse_telephone_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_adresse_telephone', self.pdf_adresse_telephone
        )

    @api.multi
    def set_pdf_adresse_mobile_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_adresse_mobile', self.pdf_adresse_mobile
        )

    @api.multi
    def set_pdf_adresse_fax_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_adresse_fax', self.pdf_adresse_fax
        )

    @api.multi
    def set_pdf_adresse_email_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_adresse_email', self.pdf_adresse_email
        )

    @api.multi
    def set_pdf_display_product_ref_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_display_product_ref', self.pdf_display_product_ref
        )

    @api.multi
    def set_pdf_mention_legale_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_mention_legale', self.pdf_mention_legale
        )

    @api.multi
    def set_pdf_masquer_pastille_commercial(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_masquer_pastille_commercial', self.pdf_masquer_pastille_commercial)
