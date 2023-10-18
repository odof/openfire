# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'of.readgroup']

    of_brand_distributeur_ids = fields.Many2many(
        'of.product.brand', 'of_res_partner_product_brand_rel', 'partner_id', 'brand_id', string=u"Marques distribuées")
    of_gb_marque_distributeur_id = fields.Many2one('of.product.brand', store=False, search='_search_gb_marque_distributeur_id',
        string=u'Regrouper par étiquette fournisseur', of_custom_groupby=True)

    def _search_gb_marque_distributeur_id(self, operator, value):
        return [('of_brand_distributeur_ids', operator, value)]

    @api.model
    def _read_group_process_groupby(self, gb, query):
        if gb != 'of_gb_marque_distributeur_id':
            return super(ResPartner, self)._read_group_process_groupby(gb, query)

        if gb == 'of_gb_marque_distributeur_id':
            alias, _ = query.add_join(
                (self._table, 'of_res_partner_product_brand_rel', 'id', 'partner_id', 'of_brand_distributeur_ids'),
                implicit=False, outer=True,
            )
            qualified_field = '"%s".brand_id' % (alias,)

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': qualified_field
        }

