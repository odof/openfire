# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    of_brand_id = fields.Many2one("of.product.brand", "Marque", readonly=True)
    of_diff_price = fields.Float(u"Δ% HT", compute="_compute_dummy")
    of_diff_qty = fields.Float(u"Δ% qté ", compute="_compute_dummy")

    of_my_company = fields.Boolean(
        string=u"Est mon magasin ?", compute='_get_is_my_company', search='_search_is_my_company')

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
        """ Sert uniquement à avoir des champs calculés que l'on peuple plus tard.
        """
        return

    def _select(self):
        res = super(AccountInvoiceReport, self)._select()
        res += ", sub.of_brand_id as of_brand_id"
        return res

    def _sub_select(self):
        res = super(AccountInvoiceReport, self)._sub_select()
        res += ", pt.brand_id as of_brand_id"
        return res

    def _from(self):
        res = super(AccountInvoiceReport, self)._from()
        res += "LEFT JOIN of_product_brand b on pt.brand_id = b.id\n"
        return res

    def _group_by(self):
        res = super(AccountInvoiceReport, self)._group_by()
        res += ", pt.brand_id"
        return res

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(AccountInvoiceReport, self)._read_group_raw(domain, fields, groupby, offset, limit, orderby, lazy)
        # Si aucune données de facturation, on retourne tel quel
        if not res:
            return res
        time_groupbys = ('date:month', 'date:year', 'date')
        # Les deltas dépendent d'un champ qui doit être calculé
        diff_percent = [vals for vals in (('of_diff_price', 'price_total'),
                                          ('of_diff_qty', 'product_qty'))
                        if vals[0] in fields and vals[1] in fields]
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
            periods = sorted(list(set([r[time_gb] for r in res])))
            others = other_gb and sorted(list(set([r[other_gb] for r in res]))) or [other_gb]

            # Mise en ordre des données pour traitement
            values = {period: {other: False for other in others} for period in periods}
            for r in res:
                values[r[time_gb]][other_gb and r[other_gb]] = r
                for f1, _ in diff:
                    r[f1] = False
                for f1, _ in diff_percent:
                    r[f1] = False

            period_prec = periods[0]
            for period in periods[1:]:
                for other in others:
                    r = values[period][other]
                    if r and values[period_prec][other]:
                        for field1, field2 in diff:
                            r[field1] = r[field2] - values[period_prec][other][field2]
                        for field1, field2 in diff_percent:
                            r[field1] = ((r[field2] / values[period_prec][other][field2] - 1)) * 100 \
                                if values[period_prec][other][field2] else 100
                period_prec = period

        return res
