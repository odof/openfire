# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleReport(models.Model):
    _inherit = "sale.report"

    of_brand_id = fields.Many2one("of.product.brand", "Marque", readonly=True)
    of_margin_percentage = fields.Float(u"Marge (%)", compute="_compute_dummy")
    of_diff_price = fields.Float(u"Δ% HT", compute="_compute_dummy")
    of_diff_margin = fields.Float(u"Δ% Marge", compute="_compute_dummy")
    of_diff_qty_delivered = fields.Float(u"Δ% qté liv.", compute="_compute_dummy")
    of_confirmation_date = fields.Datetime('Date de confirmation', readonly=True)
    of_date_livraison = fields.Datetime('Date de livraison', readonly=True)
    of_montant_livre = fields.Float(string=u"Montant livré", readonly=True)

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
        """
        Si le bon de commande est à l'état 'fait', on récupère la date de livraison
        :todo: Afficher le montant correspondant à la marchandise livrée.
        """
        res = super(SaleReport, self)._select()
        res += (", t.brand_id as of_brand_id"
                ", s.confirmation_date as of_confirmation_date"
                ", CASE WHEN sm.qty = sum(l.product_uom_qty / u.factor * u2.factor) THEN sm.date ELSE NULL END AS of_date_livraison"
                ", CASE WHEN sum(l.product_uom_qty / u.factor * u2.factor) != 0 THEN sum(l.price_subtotal / COALESCE(cr.rate, 1.0)) * sm.qty / sum(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS of_montant_livre")
        return res

    def _from(self):
        """
        Si la totalité de la quantité commandée est livrée, on renseigne la date de livraison.
        """
        res = super(SaleReport, self)._from()
        res += """
        LEFT JOIN of_product_brand b on (t.brand_id=b.id)
        LEFT JOIN (
          SELECT
            po.sale_line_id AS sol_id,
            SUM(sm.product_uom_qty) AS qty,
            max(sm.date) AS date
          FROM procurement_order po
            INNER JOIN stock_move sm ON (sm.procurement_id=po.id)
            INNER JOIN sale_order_line sol ON (sol.id=po.sale_line_id)
          WHERE sm.state = 'done'
          GROUP BY po.sale_line_id, sol.product_uom_qty
        ) AS sm ON sm.sol_id = l.id
        """
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += ", t.brand_id, s.confirmation_date, sm.date, sm.qty"
        return res

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(SaleReport, self)._read_group_raw(domain, fields, groupby, offset, limit, orderby, lazy)
        if res:
            time_groupbys = ('date:month', 'date:year', 'date', 'of_confirmation_date', 'of_confirmation_date:month', 'of_confirmation_date:year',
                             'of_date_livraison', 'of_date_livraison:month', 'of_date_livraison:year')
            # Les deltas dépendent d'un champ qui doit être calculé
            diff_percent = [vals for vals in (('of_diff_price', 'price_subtotal'),
                                              ('of_diff_margin', 'margin'),
                                              ('of_diff_qty_delivered', 'qty_delivered'))
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
                                r[field1] = ((r[field2] / values[period_prec][other][field2] - 1)) * 100 if values[period_prec][other][field2] else 100
                    period_prec = period

            display_margin_percent = ('of_margin_percentage', 'margin', 'price_subtotal')
            if all(val in fields for val in display_margin_percent):
                for entry in res:
                    if entry[display_margin_percent[1]] is not None and entry[display_margin_percent[2]] is not None:
                        entry[display_margin_percent[0]] = \
                            entry[display_margin_percent[1]] * 100 / (entry[display_margin_percent[2]] or 1)
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        fields_copy = fields
        if 'price_subtotal' not in fields_copy:
            fields_copy.append('price_subtotal')
        if 'margin' not in fields_copy:
            fields_copy.append('margin')
        if 'of_margin_percentage' not in fields_copy:
            fields_copy.append('of_margin_percentage')
        if 'of_diff_margin' not in fields_copy:
            fields_copy.append('of_diff_margin')
        if 'of_diff_price' not in fields_copy:
            fields_copy.append('of_diff_price')
        if 'qty_delivered' not in fields_copy:
            fields_copy.append('qty_delivered')
        if 'of_diff_qty_delivered' not in fields_copy:
            fields_copy.append('of_diff_qty_delivered')
        if 'of_montant_livre' not in fields_copy:
            fields_copy.append('of_montant_livre')
        return super(SaleReport, self).read_group(
            domain, fields_copy, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
