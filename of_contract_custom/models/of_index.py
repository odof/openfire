# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfIndex(models.Model):
    _name = 'of.index'

    name = fields.Char(string="Nom de l'indice")
    category_ids = fields.Many2many(
        comodel_name='product.category', string=u"Catégories d'articles", required=True)
    product_ids = fields.Many2many(comodel_name='product.template', string=u"Articles")
    index_formula = fields.Char(string="Formule d'indexation")
    index_line_ids = fields.One2many(
        comodel_name='of.index.line', inverse_name='index_id', string="Historique", required=True)

    @api.multi
    def _get_indexed_price(self, price, date=fields.Date.today()):
        """ Renvoi le prix indexé en fonction de la date """
        if not price:
            return 0.0
        today = date
        lines = self.index_line_ids.filtered(lambda l: l.date_start <= today <= l.date_end)
        if not lines or len(lines) > 1:
            return price
        return price * lines.value


class OfIndexLine(models.Model):
    _name = 'of.index.line'

    index_id = fields.Many2one(comodel_name='of.index', string="Indice", required=True)
    value = fields.Float(string="Valeur de l'indexation", required=True)
    date_start = fields.Date(string=u"Date de début", required=True)
    date_end = fields.Date(string=u"Date de fin", required=True)
