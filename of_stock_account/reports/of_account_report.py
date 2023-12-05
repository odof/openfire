# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    of_brand_id = fields.Many2one(comodel_name='of.product.brand', string="Brand", readonly=True)
    of_diff_price = fields.Float(string="Δ% HT", compute='_compute_dummy')
    of_diff_qty = fields.Float(string="Δ% Qty", compute='_compute_dummy')
    of_my_company = fields.Boolean(string="Is my store ?", compute='_get_is_my_company', search='_search_is_my_company')

    @api.model
    def _search_is_my_company(self, operator, value):
        if operator != '=' or not value:
            raise ValueError(_("Unsupported search operator"))
        return [('company_id', '=', self.env.user.company_id.id)]

    def _get_is_my_company(self):
        for rec in self:
            rec.of_my_company = self.env.user.company_id == rec.company_id

    @api.depends()
    def _compute_dummy(self):
        """Dummy method to allow to search on computed fields.
        Thoses fields should be comptued on the fly after with the values of the previous period
        """
        pass

    def _from(self):
        from_str = super()._from()
        from_str += """
            LEFT JOIN of_product_brand b on template.brand_id = b.id"""
        return from_str

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # FIXME: Is that ok ?
        # Workarround to remove unstored computed field of the fields list, beacause we can't send non stored
        # field no more here. Theses fields should be comptued on the fly after with the values of the previous period
        depends_mapping = {
            'of_diff_price': ('of_diff_price', 'price_subtotal'),
            'of_diff_qty': ('of_diff_qty', 'quantity'),
        }
        of_compute_fields = [
            f.name for f in self._fields.values() if f.name in depends_mapping and not f.store and not f.search
        ]
        fields_copy = [f for f in fields if f not in tuple(map(lambda e: f'{e}:sum', of_compute_fields))]
        res = super()._read_group_raw(domain, fields_copy, groupby, offset, limit, orderby, lazy)
        if not res:  # No data, no need to compute
            return res

        time_groupbys = ('invoice_date:month', 'invoice_date:year', 'invoice_date')
        # Les deltas dépendent d'un champ qui doit être calculé
        diff_percent = [v for v in depends_mapping.values() if f'{v[0]}:sum' in fields and f'{v[1]}:sum' in fields]
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
            # On filtre les valeurs False pour les périodes qui n'ont pas de données
            periods = sorted(list({r[time_gb] for r in res if r[time_gb]})) + list(
                {False for r in res if not r[time_gb]}
            )
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
                                ((r[field2] / values[period_prec][other][field2] - 1)) * 100
                                if values[period_prec][other][field2]
                                else 100
                            )
                period_prec = period

        return res
