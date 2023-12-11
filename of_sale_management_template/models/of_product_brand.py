# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFProductBrand(models.Model):
    _inherit = 'of.product.brand'

    @api.multi
    def write(self, vals):
        """ Permet de mettre à jour la description des lignes de modèle de devis qui contiennent un article de la marque
        si la description est la même qu'avant le write
        """
        sale_quote_line_obj = self.env['sale.quote.line']
        sale_quote_lines_to_update = sale_quote_line_obj

        if any(field in vals for field in self.quote_template_description_fields()):
            for brand in self:
                # On récupère toutes les lignes de modèle ayant un article des marques modifiées
                sale_quote_lines = sale_quote_line_obj.search(
                    [('product_id.brand_id', '=', brand.id)])
                for sale_quote_line in sale_quote_lines:
                    name = sale_quote_line.product_id.quote_template_sale_description()
                    # Si la description n'a pas été modifié sur les lignes de devis, on met ces lignes de côté
                    if name == sale_quote_line.name:
                        sale_quote_lines_to_update += sale_quote_line

        res = super(OFProductBrand, self).write(vals)

        # On met à jour ces lignes de devis avec la nouvelle description
        for line in sale_quote_lines_to_update:
            res_name = line.product_id.quote_template_sale_description()
            line.update({
                'name': res_name,
            })

        return res

    @api.model
    def quote_template_description_fields(self):
        # Si l'on modifie un des champs suivants, la description sur les ligne de modèle de devis sera modifiée
        return ['use_brand_description_sale', 'description_sale']
