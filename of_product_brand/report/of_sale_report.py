# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_brand_id = fields.Many2one(comodel_name='of.product.brand', string="Brand", readonly=True)
    of_margin_percentage = fields.Float(string="Margin (%)", compute='_compute_dummy')
    of_diff_price = fields.Float(string="Δ% HT", compute='_compute_dummy')
    of_diff_margin = fields.Float(string="Δ% Margin", compute='_compute_dummy')
    of_diff_qty_delivered = fields.Float(string="Δ% Shipped qty.", compute='_compute_dummy')
    of_confirmation_date = fields.Datetime(string="Confirmation date", readonly=True)
    of_delivery_date = fields.Datetime(string="Delivery date", readonly=True)
    of_delivered_amount = fields.Float(string="Delivered amount", readonly=True)
    of_my_company = fields.Boolean(string="Is my store ?", compute='_get_is_my_company', search='_search_is_my_company')

    @api.model
    def _search_is_my_company(self, operator, value):
        if operator != '=' or not value:
            raise ValueError(_("Unsupported search operator"))
        req = """SELECT id
            FROM sale_report
            WHERE
            company_id = %s"""
        self.env.cr.execute(
            req, (self.env.user.company_id.id,))
        line_ids = [r[0] for r in self.env.cr.fetchall()]
        return [('id', 'in', line_ids)]

    def _get_is_my_company(self):
        for rec in self:
            rec.of_my_company = self.env.user.company_id == rec.company_id

    @api.depends()
    def _compute_dummy(self):
        """ Dummy method to allow to search on computed fields.
        Thoses fields should be comptued on the fly after with the values of the previous period
        """
        pass

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['of_brand_id'] = "t.brand_id"
        # FIXME: This field is defined in a non migrated module yet
        res['of_confirmation_date'] = "NULL"
        res['of_delivery_date'] = \
            "CASE WHEN sm.qty = sum(l.product_uom_qty / u.factor * u2.factor) " \
            "    THEN sm.date ELSE NULL END"
        res['of_delivered_amount'] = "CASE WHEN sum(l.product_uom_qty / u.factor * u2.factor) != 0 THEN " \
            "    sum(l.price_subtotal / COALESCE(currency_table.rate, 1.0)) * " \
            "    sm.qty / sum(l.product_uom_qty / u.factor * u2.factor) " \
            "    ELSE 0 END"
        return res

    def _from_sale(self):
        """
        Si la totalité de la quantité commandée est livrée, on renseigne la date de livraison.
        """
        res = super()._from_sale()
        res += """
        LEFT JOIN of_product_brand b on (t.brand_id = b.id)
        LEFT JOIN (
          SELECT
            sm.sale_line_id AS sol_id,
            SUM(sm.product_uom_qty) AS qty,
            max(sm.date) AS date
          FROM procurement_group pg
            INNER JOIN stock_move sm ON (sm.group_id = pg.id)
            INNER JOIN sale_order_line sol ON (sol.id = sm.sale_line_id)
          WHERE sm.state = 'done'
          GROUP BY sm.sale_line_id, sol.product_uom_qty
        ) AS sm ON sm.sol_id = l.id
        """
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += ", t.brand_id, s.date_order, sm.date, sm.qty"
        return res

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # FIXME: Is that ok ?
        # Workarround to remove unstored computed field of the fields list, beacause we can't send non stored
        # field no more here. Thoses fields should be comptued on the fly after with the values of the previous period
        depends_mapping = {
            'of_diff_price': ('of_diff_price', 'price_subtotal'),
            'of_diff_margin': ('of_diff_margin', 'margin'),
            'of_diff_qty_delivered': ('of_diff_qty_delivered', 'qty_delivered'),
        }
        depends_mapping_margin = {
            'of_margin_percentage': ('of_margin_percentage', 'margin', 'price_total'),
        }
        fields_keys = list(depends_mapping.keys()) + list(depends_mapping_margin.keys())
        of_compute_fields = [
            f.name
            for f in self._fields.values()
            if f.name in fields_keys and not f.store and not f.search
        ]
        fields_copy = [
            f
            for f in fields
            if f not in tuple(map(lambda e: f'{e}:sum', of_compute_fields))
        ]
        res = super()._read_group_raw(domain, fields_copy, groupby, offset, limit, orderby, lazy)
        if res:
            time_groupbys = (
                'date:month', 'date:year', 'date', 'of_confirmation_date', 'of_confirmation_date:month',
                'of_confirmation_date:year', 'of_date_livraison', 'of_date_livraison:month', 'of_date_livraison:year')
            # Les deltas dépendent d'un champ qui doit être calculé
            diff_percent = [
                v
                for v in depends_mapping.values()
                if f'{v[0]}:sum' in fields and f'{v[1]}:sum' in fields
            ]
            diff = []
            if groupby and (diff or diff_percent) and any(gb in time_groupbys for gb in groupby[-2:]):
                # Regroupement des résultats par période pour calcul des deltas
                if len(groupby) == 1:
                    time_gb = groupby[-1]
                    other_gb = False
                else:
                    time_gb, other_gb = groupby[-2:]
                    if time_gb not in time_groupbys:
                        time_gb, other_gb = other_gb, time_gb

                # Liste de toutes les périodes de temps affichée, par ordre croissant
                periods = sorted(list({r[time_gb] for r in res}))
                others = other_gb and sorted(list({r[other_gb] for r in res})) or [other_gb]

                # Mise en ordre des données pour traitement
                values = {period: {other: False for other in others} for period in periods}
                for r in res:
                    values[r[time_gb]][other_gb and r[other_gb]] = r
                    for f1, _dummy in diff:
                        r[f1] = False
                    for f1, _dummy in diff_percent:
                        r[f1] = False

                period_prec = periods[0]
                for period in periods[1:]:
                    for other in others:
                        r = values[period][other]
                        if r and values[period_prec][other]:
                            for field1, field2 in diff:
                                r[field1] = r[field2] - values[period_prec][other][field2]
                            for field1, field2 in diff_percent:
                                r[field1] = (
                                    (r[field2] / values[period_prec][other][field2] - 1)
                                ) * 100 if values[period_prec][other][field2] else 100
                    period_prec = period

            display_margin_percent = depends_mapping_margin.get('of_margin_percentage')
            if all(val in fields for val in display_margin_percent):
                for entry in res:
                    entry[display_margin_percent[0]] = \
                        entry[display_margin_percent[1]] * 100 / (entry[display_margin_percent[2]] or 1)
        return res
