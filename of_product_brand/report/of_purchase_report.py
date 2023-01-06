# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    of_brand_id = fields.Many2one(comodel_name='of.product.brand', string=u"Marque", readonly=True)

    def _select_purchase_brand(self):
        return """
            , t.brand_id AS of_brand_id
            """

    def _group_by_purchase_brand(self):
        return ", t.brand_id"

    @api.model_cr
    def init(self):
        """Inject parts in the query with this hack, fetching the query and
        recreating it. Query is returned all in upper case and with final ';'.
        """
        super(PurchaseReport, self).init()
        self._cr.execute("SELECT pg_get_viewdef(%s, true)", (self._table,))
        view_def = self._cr.fetchone()[0]
        if view_def[-1] == ';':  # Remove trailing semicolon
            view_def = view_def[:-1]
        view_def = view_def.replace(
            "FROM purchase_order_line",
            "{} FROM purchase_order_line".format(
                self._select_purchase_brand()
            ),
        )
        view_def += self._group_by_purchase_brand()
        # Re-create view
        tools.drop_view_if_exists(self._cr, self._table)
        # pylint: disable=sql-injection
        self._cr.execute("create or replace view {} as ({})".format(
            self._table, view_def,
        ))
