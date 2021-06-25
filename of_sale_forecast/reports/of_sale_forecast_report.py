# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools


class OFSaleForecastReport(models.Model):
    _name = 'of.sale.forecast.report'
    _auto = False
    _description = u"Rapprot des prévisions de vente"
    _rec_name = 'id'

    date = fields.Date(string=u"Date", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string=u"Entrepôt", readonly=True)
    brand_id = fields.Many2one(comodel_name='of.product.brand', string=u"Marque", readonly=True)
    categ_id = fields.Many2one(comodel_name='product.category', string=u"Catégorie", readonly=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", readonly=True)
    quantity = fields.Float(string=u"Quantité", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_sale_forecast_report')
        self._cr.execute("""
            CREATE VIEW %s AS (
                %s
                FROM    %s
                WHERE   %s
                %s
            )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))

    def _select(self):
        return """
                SELECT  OSFOL.id                        AS id
                ,       MAKE_DATE(
                            EXTRACT(YEAR FROM OSF.forecast_date)::INTEGER,
                            OSFOL.sequence,
                            1
                        )                               AS date
                ,       OSF.company_id                  AS company_id
                ,       OSF.warehouse_id                AS warehouse_id
                ,       OSF.product_brand_id            AS brand_id
                ,       OSF.product_categ_id            AS categ_id
                ,       OSF.product_id                  AS product_id
                ,       OSFOL.forecast_qty              AS quantity
        """

    def _from(self):
        return """
                        of_sale_forecast                OSF
                ,       of_sale_forecast_overview_line  OSFOL
        """

    def _where(self):
        return """
                        OSF.state                       = 'confirm'
                AND     OSFOL.sale_forecast_id          = OSF.id
                AND     OSFOL.forecast                  = True
                """

    def _group_by(self):
        return """"""
