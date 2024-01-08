# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import _, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.tools import float_is_zero
from odoo.tools.misc import get_lang

AVAILABLE_ENCODING = [
    ('utf-8', "UTF-8"),
    ('iso-8859-1', "ISO-8859-1"),
    ('windows-1252', "Windows-1252"),
]


class OFAccountFrFec(models.TransientModel):
    _inherit = 'account.fr.fec'

    def _get_default_opening_journal_label(self):
        return "Balance initiale"

    def _get_defaut_journal_ids(self):
        return self.env['account.journal'].search([]).ids

    of_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='of_account_fec_wiz_journal_ids_rel',
        column1='wizard_id',
        column2='journal_id',
        string="Journals",
        required=True,
        default=lambda self: self._get_defaut_journal_ids(),
    )
    of_order_by = fields.Selection(
        selection=[('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string="Sort by",
        required=True,
        default='sort_date',
    )
    export_type = fields.Selection(
        selection_add=[('nonofficial_posted', "Non-official FEC report (posted entries only)")],
        ondelete={'nonofficial_posted': 'set default'},
    )
    of_file_extension = fields.Selection(
        selection=[('csv', 'CSV'), ('txt', 'TXT')], string="File extension", required=True, default='csv'
    )
    of_output_encoding = fields.Selection(
        selection=AVAILABLE_ENCODING,
        string="File encoding",
        required=True,
        default='utf-8',
    )
    of_opening_journal_code = fields.Char(string="Opening journal code", required=True, default='OUV')
    of_opening_journal_label = fields.Char(
        string="Opening Journal Label", required=True, default=lambda self: self._get_default_opening_journal_label()
    )
    of_include_opening_journal = fields.Boolean(string="Include the opening journal", default=True)
    of_use_create_date = fields.Boolean(
        string="Use creation date",
        default=False,
        help="Use the date of creation of the move instead of the date of the move.",
    )

    def _do_query_unaffected_earnings(self):
        '''Copy of l10n_fr_fec method.

        If the export type is "official", that will call the standard method.
        If the export type is "nonofficial" or "nonofficial_posted", that will return the specifics Openfire query
        with the following modifications :
            - bring customisation of the "JournalCode", "JournalLib", "EcritureNum" columns.
            - allow to use the date of creation of the move instead of the date of the move.
            Because some customers want to use the date of creation of the move for monthly export
            to an Accounting software.
        '''
        if self.export_type == 'official':
            return super()._do_query_unaffected_earnings()

        date_clause = 'am.date < %s'
        if self.of_use_create_date:
            date_clause = 'am.create_date < %s'

        debit_select = (
            "replace(CASE WHEN COALESCE(sum(aml.balance), 0) <= 0 THEN '0,00' "
            "ELSE to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',')"
        )
        credit_select = (
            "replace(CASE WHEN COALESCE(sum(aml.balance), 0) >= 0 THEN '0,00' "
            "ELSE to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',')"
        )
        sql_query = f'''
        SELECT
            %s AS JournalCode,
            %s AS JournalLib,
            %s || ' PL' AS EcritureNum,
            %s AS EcritureDate,
            '120/129' AS CompteNum,
            'Benefice (perte) reporte(e)' AS CompteLib,
            '' AS CompAuxNum,
            '' AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            {debit_select} AS Debit,
            {credit_select} AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
        WHERE
            {date_clause}
            AND am.company_id = %s
            AND aa.include_initial_balance IS NOT TRUE
            AND am.journal_id IN %s
        '''  # nosec B608

        if self.export_type == 'nonofficial_posted':
            sql_query += '''
            AND am.state = 'posted'
            '''

        company = self.env.company
        while not company.chart_template_id and company.parent_id:
            company = company.parent_id

        formatted_date_from = fields.Date.to_string(self.date_from).replace('-', '')
        args = (
            self.of_opening_journal_code,
            self.of_opening_journal_label,
            self.of_opening_journal_label,
            formatted_date_from,
            formatted_date_from,
            self.date_from,
            company.id,
            self.of_journal_ids._ids,
        )
        self._cr.execute(sql_query, args)
        row = self._cr.fetchone()
        return list(row)

    def generate_fec(self):
        '''Copy of l10n_fr_fec method.
        If the export type is "official", the FEC file will be generated by the standard method.

        If the export type is "nonofficial" or "nonofficial_posted", the FEC file will be generated with the
        specifics Openfire queries modifications :
            - allow to use the date of creation of the move instead of the date of the move.
            - allow to don't export the opening journal.
            - added a specific customisation of the file extension.
        '''
        self.ensure_one()
        if not (self.env.is_admin() or self.env.user.has_group('account.group_account_user')):
            raise AccessDenied()

        today = fields.Date.today()
        if self.date_from > today or self.date_to > today:
            raise UserError(_('You could not set the start date or the end date in the future.'))
        if self.date_from >= self.date_to:
            raise UserError(_('The start date must be inferior to the end date.'))

        company = self.env.company
        while not company.chart_template_id and company.parent_id:
            company = company.parent_id
        company_legal_data = self._get_company_legal_data(company)

        if self.export_type == 'official':  # use parent function instead
            result = super().generate_fec()
            if self.of_file_extension != 'csv':
                old_filename = self.filename
                new_filename = old_filename[:-3] + self.of_file_extension if old_filename else old_filename
                self.write({'filename': new_filename})
                result['url'] = result['url'].replace(old_filename, new_filename)
            return result

        header = [
            'JournalCode',  # 0
            'JournalLib',  # 1
            'EcritureNum',  # 2
            'EcritureDate',  # 3
            'CompteNum',  # 4
            'CompteLib',  # 5
            'CompAuxNum',  # 6  We use partner.id
            'CompAuxLib',  # 7
            'PieceRef',  # 8
            'PieceDate',  # 9
            'EcritureLib',  # 10
            'Debit',  # 11
            'Credit',  # 12
            'EcritureLet',  # 13
            'DateLet',  # 14
            'ValidDate',  # 15
            'Montantdevise',  # 16
            'Idevise',  # 17
        ]
        rows_to_write = [header]

        # INITIAL BALANCE
        unaffected_earnings_account = self.env['account.account'].search(
            [('account_type', '=', 'equity_unaffected'), ('company_id', '=', company.id)], limit=1
        )

        # used to make sure that we add the unaffected earning initial balance only once
        unaffected_earnings_line = True
        if unaffected_earnings_account:
            # compute the benefit/loss of last year to add in the initial balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        if self.pool['account.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            aa_name = f"COALESCE(aa.name->>'{lang}', aa.name->>'en_US')"
        else:
            aa_name = "aa.name"

        if self.of_include_opening_journal:
            currency_digits = 2

            opening_journal_query = self._get_opening_journal_query(aa_name)
            opening_journal_args = self._get_opening_journal_args(company)
            self._cr.execute(opening_journal_query, opening_journal_args)

            for row in self._cr.fetchall():
                listrow = list(row)
                account_id = listrow.pop()
                if not unaffected_earnings_line:
                    account = self.env['account.account'].browse(account_id)
                    if account.account_type == 'equity_unaffected':
                        # add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
                        unaffected_earnings_line = True
                        current_amount = float(listrow[11].replace(',', '.')) - float(listrow[12].replace(',', '.'))
                        unaffected_earnings_amount = float(unaffected_earnings_results[11].replace(',', '.')) - float(
                            unaffected_earnings_results[12].replace(',', '.')
                        )
                        listrow_amount = current_amount + unaffected_earnings_amount
                        if float_is_zero(listrow_amount, precision_digits=currency_digits):
                            continue
                        if listrow_amount > 0:
                            listrow[11] = str(listrow_amount).replace('.', ',')
                            listrow[12] = '0,00'
                        else:
                            listrow[11] = '0,00'
                            listrow[12] = str(-listrow_amount).replace('.', ',')
                rows_to_write.append(listrow)

        # if the unaffected earnings account wasn't in the selection yet: add it manually
        if (
            not unaffected_earnings_line
            and unaffected_earnings_results
            and (unaffected_earnings_results[11] != '0,00' or unaffected_earnings_results[12] != '0,00')
        ):
            if unaffected_earnings_account := self.env['account.account'].search(
                [
                    ('account_type', '=', 'equity_unaffected'),
                    ('company_id', '=', company.id),
                ],
                limit=1,
            ):
                unaffected_earnings_results[4] = unaffected_earnings_account.code
                unaffected_earnings_results[5] = unaffected_earnings_account.name
            rows_to_write.append(unaffected_earnings_results)

        # LINES
        lines_query = self._get_lines_query(aa_name)
        lines_agrs = self._get_lines_query_args(company)
        self._cr.execute(lines_query, lines_agrs)

        rows_to_write.extend(list(row) for row in self._cr.fetchall())
        fecvalue = self._csv_write_rows(rows_to_write)
        if self.of_output_encoding != 'utf-8':
            fecvalue = fecvalue.decode().encode('iso-8859-1')
        end_date = fields.Date.to_string(self.date_to).replace('-', '')
        self.write(
            {
                'fec_data': base64.encodebytes(fecvalue),
                'filename': f'{company_legal_data}FEC{end_date}-NONOFFICIAL.{self.of_file_extension}',
            }
        )

        url = (
            f"web/content/?model=account.fr.fec&id={str(self.id)}&"
            f"filename_field=filename&field=fec_data&download=true&filename={self.filename}"
        )
        return {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def _get_opening_journal_args(self, company):
        formatted_date_from = fields.Date.to_string(self.date_from).replace('-', '')
        return (
            self.of_opening_journal_code,
            self.of_opening_journal_label,
            self.of_opening_journal_label,
            formatted_date_from,
            formatted_date_from,
            formatted_date_from,
            self.date_from,
            company.id,
            self.of_journal_ids._ids,
        )

    def _get_opening_journal_query(self, aa_name):
        """Build the query to retrieve the opening journal entries

        :param aa_name: part of the query to get the account name
        :return: the query as a string
        """

        date_clause = 'am.date < %s'
        if self.of_use_create_date:
            date_clause = 'am.create_date < %s'

        debit_select = (
            "replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' "
            "ELSE to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',')"
        )
        credit_select = (
            "replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' "
            "ELSE to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',')"
        )
        sql_query = f'''
        SELECT
            %s AS JournalCode,
            %s AS JournalLib,
            %s || ' ' || replace(replace(MIN({aa_name}), '|', '/'), '\t', '') AS EcritureNum,
            %s AS EcritureDate,
            CASE WHEN aa.code LIKE '455%%' THEN '455000'
                WHEN aa.account_type = 'liability_payable' THEN '401000'
                WHEN aa.account_type = 'asset_receivable' THEN '411000'
                ELSE MIN(aa.code)
            END
            AS CompteNum,
            CASE WHEN aa.code LIKE '455%%' THEN 'Associés'
                WHEN aa.account_type = 'liability_payable' THEN 'Fournisseurs'
                WHEN aa.account_type = 'asset_receivable' THEN 'Clients'
                ELSE replace(replace(MIN({aa_name}), '|', '/'), '\t', '')
            END
            AS CompteLib,
            CASE WHEN aa.account_type IN ('liability_payable', 'asset_receivable') THEN aa.code
                ELSE ''
            END
            AS CompAuxNum,
            CASE WHEN aa.account_type IN ('liability_payable', 'asset_receivable') THEN replace(MIN(aa.name), '|', '/')
                ELSE ''
            END
            AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            {debit_select} AS Debit,
            {credit_select} AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise,
            MIN(aa.id) AS CompteID
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
        WHERE
            {date_clause}
            AND am.company_id = %s
            AND aa.include_initial_balance IS TRUE
            AND am.journal_id IN %s
        '''  # nosec B608

        if self.export_type == 'nonofficial_posted':
            sql_query += '''
                AND am.state = 'posted'
            '''

        sql_query += '''
        GROUP BY aml.account_id, aa.code, aa.account_type
        ORDER BY CompteNum, aa.code
        '''
        return sql_query

    def _get_lines_query_args(self, company):
        return self.date_from, self.date_to, company.id, self.of_journal_ids._ids

    def _get_lines_query(self, aa_name):
        """Build the query to retrieve the journal entries

        :param aa_name: part of the query to get the account name
        :return: the query as a string
        """
        if self.pool['account.journal'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            aj_name = f"COALESCE(aj.name->>'{lang}', aj.name->>'en_US')"
        else:
            aj_name = "aj.name"

        date_clause = 'am.date >= %s AND am.date <= %s'
        if self.of_use_create_date:
            date_clause = 'am.create_date >= %s AND am.create_date <= %s'

        debit_select = (
            "replace(CASE WHEN aml.debit = 0 THEN '0,00' ELSE to_char(aml.debit, '000000000000000D99') END, '.', ',')"
        )
        credit_select = (
            "replace(CASE WHEN aml.credit = 0 THEN '0,00' ELSE to_char(aml.credit, '000000000000000D99') END, '.', ',')"
        )
        # Il faudra ajouter les comptes de tiers nécessaires au cas par cas (Associés, Fournisseurs, Clients, etc.)
        sql_query = f'''
        SELECT
            REGEXP_REPLACE(replace(aj.code, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalCode,
            REGEXP_REPLACE(replace({aj_name}, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalLib,
            REGEXP_REPLACE(replace(am.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS EcritureNum,
            TO_CHAR(am.date, 'YYYYMMDD') AS EcritureDate,
            CASE WHEN aa.code LIKE '455%%' THEN '455000'
                 WHEN aa.account_type = 'liability_payable' THEN '401000'
                 WHEN aa.account_type = 'asset_receivable' THEN '411000'
                 ELSE aa.code
            END
            AS CompteNum,
            CASE WHEN aa.code LIKE '455%%' THEN 'Associés'
                 WHEN aa.account_type = 'liability_payable' THEN 'Fournisseurs'
                 WHEN aa.account_type = 'asset_receivable' THEN 'Clients'
                 ELSE REGEXP_REPLACE(replace({aa_name}, '|', '/'), '[\\t\\r\\n]', ' ', 'g')
            END
            AS CompteLib,
            CASE WHEN aa.account_type IN ('liability_payable', 'asset_receivable')
            THEN aa.code
            ELSE ''
            END
            AS CompAuxNum,
            CASE WHEN aa.account_type IN ('liability_payable', 'asset_receivable')
            THEN COALESCE(REGEXP_REPLACE(replace(rp.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g'), '')
            ELSE ''
            END
            AS CompAuxLib,
            CASE WHEN am.ref IS null OR am.ref = ''
            THEN '-'
            ELSE REGEXP_REPLACE(replace(am.ref, '|', '/'), '[\\t\\r\\n]', ' ', 'g')
            END
            AS PieceRef,
            TO_CHAR(COALESCE(am.invoice_date, am.date), 'YYYYMMDD') AS PieceDate,
            CASE WHEN aml.name IS NULL THEN '/'
                ELSE REGEXP_REPLACE(replace(aml.name, '|', '/'), '[\\t\\n\\r]', ' ', 'g') END AS EcritureLib,
            {debit_select} AS Debit,
            {credit_select} AS Credit,
            CASE WHEN rec.name IS NULL THEN '' ELSE rec.name END AS EcritureLet,
            CASE WHEN aml.full_reconcile_id IS NULL THEN '' ELSE TO_CHAR(rec.create_date, 'YYYYMMDD') END AS DateLet,
            TO_CHAR(am.date, 'YYYYMMDD') AS ValidDate,
            CASE
                WHEN aml.amount_currency IS NULL OR aml.amount_currency = 0 THEN ''
                ELSE replace(to_char(aml.amount_currency, '000000000000000D99'), '.', ',')
            END AS Montantdevise,
            CASE WHEN aml.currency_id IS NULL THEN '' ELSE rc.name END AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            LEFT JOIN res_partner rp ON rp.id=aml.partner_id
            JOIN account_journal aj ON aj.id = am.journal_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN res_currency rc ON rc.id = aml.currency_id
            LEFT JOIN account_full_reconcile rec ON rec.id = aml.full_reconcile_id
        WHERE
            {date_clause}
            AND am.company_id = %s
            AND am.journal_id IN %s
        '''  # nosec B608

        if self.export_type == 'nonofficial_posted':
            sql_query += '''
            AND am.state = 'posted'
            '''

        order_by = 'am.date, am.name, aml.id'
        if self.of_order_by == 'sort_journal_partner':
            order_by = 'aj.code, rp.name, aml.id'
        sql_query += f'''
        ORDER BY {order_by}
        '''
        return sql_query
