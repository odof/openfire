# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_discount_product_categ_ids_setting = fields.Many2many(
        comodel_name='product.category',
        string=u"(OF) Catégorie des remises",
        help=u"Catégorie des articles utilisés pour les remises"
    )
    of_create_analyse_auto = fields.Boolean(
        string=u"(OF) Analyse de chantier",
        help=u"Rend la création d'analyse de chantier automatique à la validation de la commande"
    )

    @api.multi
    def set_of_discount_product_categ_ids_setting(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings',
            'of_discount_product_categ_ids_setting',
            self.of_discount_product_categ_ids_setting._ids
        )

    @api.multi
    def set_of_create_analyse_auto_setting(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_create_analyse_auto', self.of_create_analyse_auto)


