# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools


class StockHistory(models.Model):
    _inherit = 'stock.history'

    of_internal_serial_number = fields.Char(string=u"Numéro de série interne", readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'stock_history')
        self._cr.execute("""
            CREATE VIEW stock_history AS (
  SELECT MIN(id) as id,
    move_id,
    location_id,
    company_id,
    product_id,
    product_categ_id,
    product_template_id,
    SUM(quantity) as quantity,
    date,
    COALESCE(SUM(price_unit_on_quant * quantity) / NULLIF(SUM(quantity), 0), 0) as price_unit_on_quant,
    source,
    string_agg(DISTINCT serial_number, ', ' ORDER BY serial_number) AS serial_number,
    string_agg(DISTINCT of_internal_serial_number, ', ' ORDER BY of_internal_serial_number) AS of_internal_serial_number
    FROM
    ((SELECT
        stock_move.id AS id,
        stock_move.id AS move_id,
        dest_location.id AS location_id,
        dest_location.company_id AS company_id,
        stock_move.product_id AS product_id,
        product_template.id AS product_template_id,
        product_template.categ_id AS product_categ_id,
        quant.qty AS quantity,
        stock_move.date AS date,
        quant.cost as price_unit_on_quant,
        stock_move.origin AS source,
        stock_production_lot.name AS serial_number,
        stock_production_lot.of_internal_serial_number AS of_internal_serial_number
    FROM
        stock_quant as quant
    JOIN
        stock_quant_move_rel ON stock_quant_move_rel.quant_id = quant.id
    JOIN
        stock_move ON stock_move.id = stock_quant_move_rel.move_id
    LEFT JOIN
        stock_production_lot ON stock_production_lot.id = quant.lot_id
    JOIN
        stock_location dest_location ON stock_move.location_dest_id = dest_location.id
    JOIN
        stock_location source_location ON stock_move.location_id = source_location.id
    JOIN
        product_product ON product_product.id = stock_move.product_id
    JOIN
        product_template ON product_template.id = product_product.product_tmpl_id
    WHERE quant.qty>0 AND stock_move.state = 'done' AND dest_location.usage in ('internal', 'transit')
    AND (
        not (source_location.company_id is null and dest_location.company_id is null) or
        source_location.company_id != dest_location.company_id or
        source_location.usage not in ('internal', 'transit'))
    ) UNION ALL
    (SELECT
        (-1) * stock_move.id AS id,
        stock_move.id AS move_id,
        source_location.id AS location_id,
        source_location.company_id AS company_id,
        stock_move.product_id AS product_id,
        product_template.id AS product_template_id,
        product_template.categ_id AS product_categ_id,
        - quant.qty AS quantity,
        stock_move.date AS date,
        quant.cost as price_unit_on_quant,
        stock_move.origin AS source,
        stock_production_lot.name AS serial_number,
        stock_production_lot.of_internal_serial_number AS of_internal_serial_number
    FROM
        stock_quant as quant
    JOIN
        stock_quant_move_rel ON stock_quant_move_rel.quant_id = quant.id
    JOIN
        stock_move ON stock_move.id = stock_quant_move_rel.move_id
    LEFT JOIN
        stock_production_lot ON stock_production_lot.id = quant.lot_id
    JOIN
        stock_location source_location ON stock_move.location_id = source_location.id
    JOIN
        stock_location dest_location ON stock_move.location_dest_id = dest_location.id
    JOIN
        product_product ON product_product.id = stock_move.product_id
    JOIN
        product_template ON product_template.id = product_product.product_tmpl_id
    WHERE quant.qty>0 AND stock_move.state = 'done' AND source_location.usage in ('internal', 'transit')
    AND (
        not (dest_location.company_id is null and source_location.company_id is null) or
        dest_location.company_id != source_location.company_id or
        dest_location.usage not in ('internal', 'transit'))
    ))
    AS foo
    GROUP BY move_id, location_id, company_id, product_id, product_categ_id, date, source, product_template_id
            )""")
