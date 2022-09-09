# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def write(self, vals):
        """ Permet de mettre à jour la description des lignes de modèle de devis qui contienne cet article
        si la description est la même qu'avant le write
        """
        sale_quote_line_obj = self.env['sale.quote.line']
        sale_quote_lines_to_update = sale_quote_line_obj

        # Si l'on modifie un des champs suivants, la description sera modifiée
        if any(field in vals for field in ['default_code', 'name', 'description_sale', 'attribute_value_ids']):
            for product in self.mapped('product_variant_ids'):
                name = product.name_get()[0][1]
                if product.description_sale:
                    name += '\n' + product.description_sale

                # Si la description n'a pas été modifié sur les lignes de devis, on met ces lignes de côté
                sale_quote_lines_to_update += sale_quote_line_obj.search(
                    [('product_id', '=', product.id), ('name', '=', name)])

        res = super(ProductTemplate, self).write(vals)

        # On met à jour ces lignes de devis avec la nouvelle description
        for line in sale_quote_lines_to_update:
            res_name = line.product_id.name_get()[0][1]
            if line.product_id.description_sale:
                res_name += '\n' + line.product_id.description_sale
            line.update({
                'name': res_name,
            })

        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def write(self, vals):
        """ Permet de mettre à jour la description des lignes de modèle de devis qui contienne cet article
        si la description est la même qu'avant le write
        """
        sale_quote_line_obj = self.env['sale.quote.line']
        sale_quote_lines_to_update = sale_quote_line_obj

        # Si l'on modifie un des champs suivants, la description sera modifiée
        if any(field in vals for field in ['default_code', 'name', 'description_sale', 'attribute_value_ids']):
            for product in self:
                name = product.name_get()[0][1]
                if product.description_sale:
                    name += '\n' + product.description_sale

                # Si la description n'a pas été modifié sur les lignes de devis, on met ces lignes de côté
                sale_quote_lines_to_update += sale_quote_line_obj.search(
                    [('product_id', '=', product.id), ('name', '=', name)])

        res = super(ProductProduct, self).write(vals)

        # On met à jour ces lignes de devis avec la nouvelle description
        for line in sale_quote_lines_to_update:
            res_name = line.product_id.name_get()[0][1]
            if line.product_id.description_sale:
                res_name += '\n' + line.product_id.description_sale
            line.update({
                'name': res_name,
            })

        return res
