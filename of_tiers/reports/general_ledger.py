# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GeneralLedgerReport(models.TransientModel):
    _inherit = 'report_general_ledger_qweb'

    of_receivable_account_id = fields.Many2one('account.account', string="Regroupement des comptes client")
    of_payable_account_id = fields.Many2one('account.account', string="Regroupement des comptes fournisseur")

    @api.multi
    def compute_data_for_report(self, with_line_details=True, with_partners=True):
        super(GeneralLedgerReport, self).compute_data_for_report(
            with_line_details=with_line_details, with_partners=with_partners)
        # Si un compte de centralisation est renseigné, on fusionne tous les comptes de tiers
        cr = self.env.cr
        query_select_ra = """
SELECT ra.id
FROM report_general_ledger_qweb_account ra
INNER JOIN account_account a ON a.id = ra.account_id
WHERE ra.report_id = %s
  AND a.internal_type = %s
"""
        query_insert_ra = """
INSERT INTO
    report_general_ledger_qweb_account
    (
    report_id,
    create_uid,
    create_date,
    account_id,
    code,
    name,
    initial_debit,
    initial_credit,
    initial_balance,
    final_debit,
    final_credit,
    final_balance,
    is_partner_account
    )
SELECT
    %s AS report_id,
    %s AS create_uid,
    NOW() AS create_date,
    %s AS account_id,
    %s AS code,
    %s AS name,
    SUM(initial_debit) AS initial_debit,
    SUM(initial_credit) AS initial_credit,
    SUM(initial_balance) AS initial_balance,
    SUM(final_debit) AS final_debit,
    SUM(final_credit) AS final_credit,
    SUM(final_balance) AS final_balance,
    true AS is_partner_account
FROM
    report_general_ledger_qweb_account ra
WHERE
    ra.id IN %s
RETURNING id
"""
        query_update_rp = """
UPDATE report_general_ledger_qweb_partner
SET report_account_id = %s
WHERE report_account_id IN %s
"""
        query_select_rp = """
SELECT id
FROM report_general_ledger_qweb_partner
WHERE report_account_id IN %s
AND id iN (
    SELECT partner_id
    FROM report_general_ledger_qweb_partner
    WHERE report_account_id IN %s
    GROUP BY partner_id
    HAVING COUNT(*) > 1
    )
"""
        query_insert_rp = """
INSERT INTO
    report_general_ledger_qweb_partner
    (
    report_account_id,
    create_uid,
    create_date,
    partner_id,
    name,
    initial_debit,
    initial_credit,
    initial_balance,
    final_debit,
    final_credit,
    final_balance
    )
SELECT
    %s AS report_account_id,
    %s AS create_uid,
    NOW() AS create_date,
    rp.partner_id,
    rp.partner_name,
    SUM(initial_debit) AS initial_debit,
    SUM(initial_credit) AS initial_credit,
    SUM(initial_balance) AS initial_balance,
    SUM(final_debit) AS final_debit,
    SUM(final_credit) AS final_credit,
    SUM(final_balance) AS final_balance,
FROM
    report_general_ledger_qweb_partner rp
WHERE
    id IN %s
GROUP BY rp.partner_id, rp.partner_name
"""

        query_delete_rp = "DELETE FROM report_general_ledger_qweb_partner WHERE id IN %s"
        query_delete_ra = "DELETE FROM report_general_ledger_qweb_account WHERE id IN %s"

        for account, internal_type in ((self.of_receivable_account_id, 'receivable'),
                                       (self.of_payable_account_id, 'payable')):
            if account:
                cr.execute(query_select_ra, (self.id, internal_type))
                ra_ids = tuple([row[0] for row in cr.fetchall()])
                if not ra_ids:
                    continue
                cr.execute(
                    query_insert_ra,
                    (
                        self.id,
                        self.env.uid,
                        account.id,
                        account.code,
                        account.name,
                        ra_ids,
                    ))
                ra_id = cr.fetchone()[0]

                # Normalement un partenaire n'a d'écritures que sur 1 seul compte de tiers.
                # Il suffit donc de modifier le report_account_id des lignes de report_general_ledger_qweb_partner
                # Pour les quelques exceptions (e.g. partenaire avec écritures sur compte dédié + 411100),
                #   on fusionne ensuite les lignes de report_general_ledger_qweb_partner
                cr.execute(query_update_rp, (ra_id, ra_ids))
                cr.execute(query_select_rp, (ra_ids, ra_ids))
                rp_ids = tuple([row[0] for row in cr.fetchall()])
                if rp_ids:
                    # Fusion des lignes
                    cr.execute(
                        query_insert_rp,
                        (
                            ra_id,
                            self.env.uid,
                            rp_ids,
                        )
                    )
                    cr.execute(query_delete_rp, (rp_ids, ))
                cr.execute(query_delete_ra, (ra_ids, ))
