# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    @api.model
    def _auto_init(self):
        """
        Certain paramètres d'affichage sont passés de Booléen à Sélection.
        Cette fonction est appelée à chaque mise à jour mais ne fait quelque chose
        que la première fois qu'elle est appelée.
        """
        super(AccountConfigSettings, self)._auto_init()
        if not self.env['ir.values'].get_default('account.config.settings', 'of_color_font'):
            self.env['ir.values'].sudo().set_default('account.config.settings', 'of_color_font', "#000000")

    pdf_vt_pastille = fields.Boolean(
        string=u"(OF) Date VT pastille", required=True, default=False,
        help=u"Afficher la date de visite technique dans une pastille dans le rapport PDF des factures ?")

    of_color_bg_section = fields.Char(
        string="(OF) Couleur fond titres section", help=u"Choisissez une couleur de fond pour les titres de section",
        default="#F0F0F0")
    of_color_font = fields.Char(
        string="(OF) Couleur police titre section", help=u"Choisissez une couleur pour les titres de section",
        default="#000000")
    of_validate_pickings = fields.Selection([
        (1, u"Ne pas gérer les BL depuis la facture"),
        (2, u"Gérer les BL après la validation de la facture"),
        (3, u"Valider les BL au moment de la validation de la facture")], string="(OF) Validation des BL", default=1)

    @api.multi
    def set_pdf_vt_pastille_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_vt_pastille', self.pdf_vt_pastille)

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'of_color_bg_section', self.of_color_bg_section)

    @api.multi
    def set_of_color_font_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'of_color_font', self.of_color_font)

    @api.multi
    def set_of_validate_pickings(self):
        view = self.env.ref('of_sale.of_account_invoice_picking_view_form')
        if view:
            view.write({'active': self.of_validate_pickings in (2, 3)})
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'of_validate_pickings', self.of_validate_pickings)
