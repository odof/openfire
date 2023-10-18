# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'of.readgroup']

    of_brand_distributor_ids = fields.Many2many(
        comodel_name='of.product.brand',
        relation='of_res_partner_product_brand_rel',
        column1='partner_id',
        column2='brand_id',
        string="Distributed brands",
    )
    of_gb_brand_distributor_id = fields.Many2one(
        comodel_name='of.product.brand',
        string="Group by supplier tags",
    )

    def _search_gb_marque_distributeur_id(self, operator, value):
        return [('of_brand_distributor_ids', operator, value)]

    @api.model
    def _read_group_process_groupby(self, gb, query):
        if gb != 'of_gb_brand_distributor_id':
            return super()._read_group_process_groupby(gb, query)

        split = gb.split(':')
        field = self._fields.get(split[0])
        if not field:
            raise ValueError("Invalid field %r on model %r" % (split[0], self._name))
        field_type = field.type
        alias = query.left_join(
            self._table, 'id', 'of_res_partner_product_brand_rel', 'partner_id', 'of_brand_distributor_ids'
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': field_type,
            'display_format': None,
            'interval': None,
            'granularity': None,
            'tz_convert': False,
            'qualified_field': f'"{alias}".brand_id',
        }
