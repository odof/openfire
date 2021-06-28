# -*- coding: utf-8 -*-

from odoo import models


class AgedPartnerBalanceReportCompute(models.TransientModel):
    _inherit = 'report_aged_partner_balance_qweb'

    def _inject_line_values(self, only_empty_partner_line=False):
        """ Inject report values for report_aged_partner_balance_qweb_line.

        Modification OpenFire : Arrondi des valeurs.
        Cela évite des affichages de pourcentages démesurés si le résiduel vaut un nombre qui devrait être 0.
        """
        query_inject_line = """
WITH
    date_range AS
        (
            SELECT
                DATE %s AS date_current,
                DATE %s - INTEGER '30' AS date_less_30_days,
                DATE %s - INTEGER '60' AS date_less_60_days,
                DATE %s - INTEGER '90' AS date_less_90_days,
                DATE %s - INTEGER '120' AS date_less_120_days
        )
INSERT INTO
    report_aged_partner_balance_qweb_line
    (
        report_partner_id,
        create_uid,
        create_date,
        partner,
        amount_residual,
        current,
        age_30_days,
        age_60_days,
        age_90_days,
        age_120_days,
        older
    )
SELECT
    rp.id AS report_partner_id,
    %s AS create_uid,
    NOW() AS create_date,
    rp.name,
    ROUND(SUM(rlo.amount_residual), 2) AS amount_residual,
    ROUND(SUM(
        CASE
            WHEN rlo.date_due >= date_range.date_current
            THEN rlo.amount_residual
        END
    ), 2) AS current,
    ROUND(SUM(
        CASE
            WHEN
                rlo.date_due >= date_range.date_less_30_days
                AND rlo.date_due < date_range.date_current
            THEN rlo.amount_residual
        END
    ), 2) AS age_30_days,
    ROUND(SUM(
        CASE
            WHEN
                rlo.date_due >= date_range.date_less_60_days
                AND rlo.date_due < date_range.date_less_30_days
            THEN rlo.amount_residual
        END
    ), 2) AS age_60_days,
    ROUND(SUM(
        CASE
            WHEN
                rlo.date_due >= date_range.date_less_90_days
                AND rlo.date_due < date_range.date_less_60_days
            THEN rlo.amount_residual
        END
    ), 2) AS age_90_days,
    ROUND(SUM(
        CASE
            WHEN
                rlo.date_due >= date_range.date_less_120_days
                AND rlo.date_due < date_range.date_less_90_days
            THEN rlo.amount_residual
        END
    ), 2) AS age_120_days,
    ROUND(SUM(
        CASE
            WHEN rlo.date_due < date_range.date_less_120_days
            THEN rlo.amount_residual
        END
    ), 2) AS older
FROM
    date_range,
    report_open_items_qweb_move_line rlo
INNER JOIN
    report_open_items_qweb_partner rpo ON rlo.report_partner_id = rpo.id
INNER JOIN
    report_open_items_qweb_account rao ON rpo.report_account_id = rao.id
INNER JOIN
    report_aged_partner_balance_qweb_account ra ON rao.code = ra.code
INNER JOIN
    report_aged_partner_balance_qweb_partner rp
        ON
            ra.id = rp.report_account_id
        """
        if not only_empty_partner_line:
            query_inject_line += """
        AND rpo.partner_id = rp.partner_id
            """
        elif only_empty_partner_line:
            query_inject_line += """
        AND rpo.partner_id IS NULL
        AND rp.partner_id IS NULL
            """
        query_inject_line += """
WHERE
    rao.report_id = %s
AND ra.report_id = %s
GROUP BY
    rp.id
        """
        query_inject_line_params = (self.date_at,) * 5
        query_inject_line_params += (
            self.env.uid,
            self.open_items_id.id,
            self.id,
        )
        self.env.cr.execute(query_inject_line, query_inject_line_params)
