# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductCategory(models.Model):
    _inherit = "product.category"

    type = fields.Selection([
        ('view', 'Vue'),
        ('normal', 'Normale'),
        ('escompte', 'Escompte')])

class ProductTemplate(models.Model):
    _inherit = "product.template"

    categ_id = fields.Many2one(domain="[('type','in',('normal', 'escompte'))]")

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    of_type_escompte = fields.Boolean(string=u"Type escompte", compute="_is_escompte")

    @api.depends('product_id')
    def _is_escompte(self):
        for line in self:
            line.of_type_escompte = line.product_id and line.product_id.categ_id.type == "escompte"

    @api.onchange('price_unit', 'quantity', 'of_type_escompte')
    def _onchange_detect_non_negative_escompte(self):
        if self.price_unit * self.quantity > 0 and self.of_type_escompte:
            self.price_unit = 0
            warning = {
                'title': ('Attention!'),
                'message': (u"Le montant de l'escompte doit être négatif"),
            }
            return {'warning': warning}
