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

        if any(field in vals for field in self.quote_template_description_fields()):
            for product in self.mapped('product_variant_ids'):
                name = product.quote_template_sale_description()
                # Si la description n'a pas été modifié sur les lignes de devis, on met ces lignes de côté
                sale_quote_lines_to_update += sale_quote_line_obj.search(
                    [('product_id', '=', product.id), ('name', '=', name)])

        res = super(ProductTemplate, self).write(vals)

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
        return ['default_code', 'name', 'description_sale', 'attribute_value_ids']

    @api.multi
    def quote_template_sale_description(self):
        self.ensure_one()
        name = self.name_get()[0][1]
        if self.description_sale:
            name += '\n' + self.description_sale
        if self.brand_id.use_brand_description_sale:
            # Recalcul du libellé de la ligne
            name = self.name_get()[0][1]
            brand_desc = self.env['mail.template'].with_context(safe=True).render_template(
                self.brand_id.description_sale, self._name, self.id, post_process=False)
            name += u'\n%s' % brand_desc
        if self.brand_id.show_in_sales:
            # Ajout de la marque dans le descriptif de l'article
            brand_code = self.brand_id.name + ' - '
            if name[0] == '[':
                i = name.find(']') + 1
                if name[i] == ' ':
                    i += 1
                name = name[:i] + brand_code + name[i:]
            else:
                name = brand_code + name
        return name

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def write(self, vals):
        """ Permet de mettre à jour la description des lignes de modèle de devis qui contienne cet article
        si la description est la même qu'avant le write
        """
        sale_quote_line_obj = self.env['sale.quote.line']
        sale_quote_lines_to_update = sale_quote_line_obj

        if any(field in vals for field in self.quote_template_description_fields()):
            for product in self:
                name = product.quote_template_sale_description()
                # Si la description n'a pas été modifié sur les lignes de devis, on met ces lignes de côté
                sale_quote_lines_to_update += sale_quote_line_obj.search(
                    [('product_id', '=', product.id), ('name', '=', name)])

        res = super(ProductProduct, self).write(vals)

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
        return ['default_code', 'name', 'description_sale', 'attribute_value_ids']

    @api.multi
    def quote_template_sale_description(self):
        self.ensure_one()
        name = self.name_get()[0][1]
        if self.description_sale:
            name += '\n' + self.description_sale
        if self.brand_id.use_brand_description_sale:
            # Recalcul du libellé de la ligne
            name = self.name_get()[0][1]
            brand_desc = self.env['mail.template'].with_context(safe=True).render_template(
                self.brand_id.description_sale, self._name, self.id, post_process=False)
            name += u'\n%s' % brand_desc
        if self.brand_id.show_in_sales:
            # Ajout de la marque dans le descriptif de l'article
            brand_code = self.brand_id.name + ' - '
            if name[0] == '[':
                i = name.find(']') + 1
                if name[i] == ' ':
                    i += 1
                name = name[:i] + brand_code + name[i:]
            else:
                name = brand_code + name
        return name
