# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def _auto_init(self):
        """
        Certains paramètres d'affichage sont passés de Booléen à Sélection.
        Cette fonction est appelée à chaque mise à jour, mais ne fait quelque chose
        que la première fois qu'elle est appelée.
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

        if not self.env['ir.values'].search(
                [('name', '=', 'of_propagate_payment_term'), ('model', '=', 'sale.config.settings')]):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_propagate_payment_term', True)

    of_deposit_product_categ_id_setting = fields.Many2one(
        'product.category',
        string=u"(OF) Catégorie des acomptes",
        help=u"Catégorie des articles utilisés pour les acomptes"
    )

    stock_warning_setting = fields.Boolean(
        string="(OF) Stock", required=True, default=False,
        help=u"Afficher les messages d'avertissement de stock ?"
    )

    of_position_fiscale = fields.Boolean(string="(OF) Position fiscale")
    of_allow_quote_addition = fields.Boolean(string=u"(OF) Devis complémentaires")

    group_of_afficher_total_ttc = fields.Boolean(
        string=u"(OF) Afficher les sous-totaux TTC par ligne de commande", default=False,
        help=u"Affiche les sous-totaux TTC par ligne de commande. Uniquement dans le formulaire et non dans les "
             u"rapports.", implied_group='of_sale.group_of_afficher_total_ttc', group='base.group_user')

    group_of_order_line_option = fields.Boolean(
        string=u"(OF) Options de ligne de commande", implied_group='of_sale.group_of_order_line_option',
        group='base.group_portal,base.group_user,base.group_public')

    group_of_sale_multiimage = fields.Selection([
        (0, 'One image per product'),
        (1, 'Several images per product')],
        string='(OF) Multi Images', implied_group='of_sale.group_of_sale_multiimage',
        group='base.group_portal,base.group_user,base.group_public')

    of_sale_print_multiimage_level = fields.Selection([
        (0, 'Do not print'),
        (1, 'Print on each line'),
        (2, 'Print on appendix')], string='(OF) Print product images on Sale Order')
    group_of_sale_print_one_image = fields.Boolean(
        'Print on each line', implied_group='of_sale.group_of_sale_print_one_image',
        group='base.group_portal,base.group_user,base.group_public')
    group_of_sale_print_multiimage = fields.Boolean(
        'Print on appendix', implied_group='of_sale.group_of_sale_print_multiimage',
        group='base.group_portal,base.group_user,base.group_public')

    group_of_sale_print_attachment = fields.Selection([
        (0, 'Do not print'),
        (1, 'Print on appendix')], string='(OF) Print product attachments on Sale Order',
        implied_group='of_sale.group_of_sale_print_attachment',
        group='base.group_portal,base.group_user,base.group_public')

    of_invoice_grouped = fields.Selection(selection=[
        (0, 'Groupement par partenaire + devise'),
        (1, 'Groupement par commande'), ], string=u"(OF) Facturation groupée")

    sale_show_tax = fields.Selection(selection_add=[('both', 'Afficher les sous-totaux HT (B2B) et TTC (B2C)')])

    of_propagate_payment_term = fields.Boolean(
        string=u"(OF) Terms of payment",
        help=u"Si décoché, les conditions de règlement ne sont pas propagées aux factures", default=True)

    of_sale_order_margin_control = fields.Boolean(
        string=u"(OF) Contrôle de marge", help=u"Activer le contrôle de marge à la validation des commandes")

    @api.multi
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'stock_warning_setting', self.stock_warning_setting)

    @api.multi
    def set_of_deposit_product_categ_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_deposit_product_categ_id_setting', self.of_deposit_product_categ_id_setting.id)

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

    @api.multi
    def set_of_sale_print_multiimage_level_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_sale_print_multiimage_level', self.of_sale_print_multiimage_level)

    @api.onchange('of_sale_print_multiimage_level')
    def onchange_of_sale_print_multiimage_level(self):
        self.group_of_sale_print_one_image = self.of_sale_print_multiimage_level == 1
        self.group_of_sale_print_multiimage = self.of_sale_print_multiimage_level == 2

    @api.onchange('sale_show_tax')
    def _onchange_sale_tax(self):
        # Erase and replace parent function
        if self.sale_show_tax == "subtotal":
            self.update({
                'group_show_price_total': False,
                'group_show_price_subtotal': True,
            })
        elif self.sale_show_tax == "total":
            self.update({
                'group_show_price_total': True,
                'group_show_price_subtotal': False,
            })
        else:
            self.update({
                'group_show_price_total': True,
                'group_show_price_subtotal': True,
            })

    @api.multi
    def set_of_propagate_payment_term(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_propagate_payment_term', self.of_propagate_payment_term)

    @api.multi
    def set_of_sale_order_margin_control(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_sale_order_margin_control', self.of_sale_order_margin_control)

    @api.multi
    def action_printings_params(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.sale.wizard.set.printing.params',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new'
        }
