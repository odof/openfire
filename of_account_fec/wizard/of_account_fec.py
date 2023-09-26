# -*- coding:utf-8 -*-

import base64
import csv
import StringIO

from odoo import api, fields, models, _
from odoo.exceptions import Warning, AccessDenied


# liste des encodages les plus utilisés, seuls les encodages régulièrement utilisés en France sont non commentés
available_encodings = [
    ('utf-8', u"UTF-8"),
    ('iso-8859-1', u"ISO-8859-1"),
    ('windows-1252', u"Windows-1252"),
    # ('windows-1251', u"Windows-1251"),
    # ('gb2312', u"GB2312"),
    # ('shift_jis', u"Shift JIS"),
    # ('gbk', u"GBK"),
    # ('euc_kr', u"EUC-KR"),
    # ('iso-8859-9', u"ISO-8859-9"),
    # ('windows-1254', u"Windows-1254"),
    # ('euc_jp', u"EUC-JP"),
    # ('big5', u"Big5"),
]


class OFAccountFrFec(models.TransientModel):
    _inherit = 'account.fr.fec'

    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, default=lambda self: self.env['account.journal'].search([]))
    sortby = fields.Selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], string='Sort by', required=True, default='sort_date')
    export_type = fields.Selection([
        ('official', 'Official'),
        ('nonofficial_posted', 'Non-official posted only'),
        ('nonofficial', 'Non-official'),
        ], string='Export Type', required=True, default='official',
        help="Export Type :\n"
             " - Official : Official FEC report (posted entries only)\n"
             " - Non-official posted only : Non-official FEC report (posted entries only)\n"
             " - Non-official : Non-official FEC report (posted and unposted entries)")
    of_extension = fields.Selection([('csv', 'csv'), ('txt', 'txt')], string="File extension", required=True, default='csv')
    of_ouv_code = fields.Char("Code du journal d'ouverture", required=True, default='OUV')
    of_ouv_name = fields.Char("Libellé du journal d'ouverture", required=True, default='Balance initiale')
    of_ouv_include = fields.Boolean(string="inclure le journal d'ouverture", default=True)
    of_encoding = fields.Selection(
        selection=available_encodings, string=u"Encodage du fichier", default=available_encodings[0][0], required=True)

    where_clause_create_date = fields.Boolean("Utiliser la date de création", required=True, default=False)

    def _do_query_unaffected_earnings(self):
        """ Compute the sum of ending balances for all accounts that are of a type that does not bring forward the balance in new fiscal years.
            This is needed because we have to display only one line for the initial balance of all expense/revenue accounts in the FEC.
            copy of parent function.
        """
        if self.export_type == 'official':  # use parent function instead
            return super(OFAccountFrFec, self)._do_query_unaffected_earnings()
        sql_query = """
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
            replace(CASE WHEN COALESCE(sum(aml.balance), 0) <= 0 THEN '0,00' ELSE to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Debit,
            replace(CASE WHEN COALESCE(sum(aml.balance), 0) >= 0 THEN '0,00' ELSE to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN account_account_type aat ON aa.user_type_id = aat.id
        WHERE
            am.company_id = %s
            AND aat.include_initial_balance = 'f'
            AND (aml.debit != 0 OR aml.credit != 0)
            AND am.journal_id IN %s
        """
        if self.where_clause_create_date:  # certains client veulent la date de création (exports mensuels vers logiciel compta)
            sql_query += """
            AND am.create_date < %s
            """
        else:
            sql_query += """
            AND am.date < %s
            """

        if self.export_type == 'nonofficial_posted':
            sql_query += """
            AND am.state = 'posted'
            """

        company = self.env.user.company_id
        while not company.chart_template_id and company.parent_id:
            company = company.parent_id
        formatted_date_from = self.date_from.replace('-', '')
        self._cr.execute(
            sql_query, (self.of_ouv_code, self.of_ouv_name, self.of_ouv_name, formatted_date_from, formatted_date_from, formatted_date_from, company.id, self.journal_ids._ids, self.date_from))
        # listrow = []
        row = self._cr.fetchone()
        listrow = list(row)
        return listrow

    @api.multi
    def generate_fec(self):
        """
        copy of parent function
        """
        self.ensure_one()
        if self.export_type == 'official':  # use parent function instead
            result = super(OFAccountFrFec, self).generate_fec()
            if self.of_extension != 'csv':
                old_filename = self.filename
                # On remplace l'extension csv par celle choisie
                new_filename = old_filename[:-3] + self.of_extension
                self.write({'filename': new_filename})
                result['url'] = result['url'].replace(old_filename, new_filename)
            return result
        if not (self.env.is_admin() or self.env.user.has_group('account.group_account_user')):
            raise AccessDenied()
        # We choose to implement the flat file instead of the XML
        # file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move
        # but Odoo has the label on the account.move.line, so that's a
        # problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
        header = [
            'JournalCode',    # 0
            'JournalLib',     # 1
            'EcritureNum',    # 2
            'EcritureDate',   # 3
            'CompteNum',      # 4
            'CompteLib',      # 5
            'CompAuxNum',     # 6  We use partner.id
            'CompAuxLib',     # 7
            'PieceRef',       # 8
            'PieceDate',      # 9
            'EcritureLib',    # 10
            'Debit',          # 11
            'Credit',         # 12
            'EcritureLet',    # 13
            'DateLet',        # 14
            'ValidDate',      # 15
            'Montantdevise',  # 16
            'Idevise',        # 17
            ]

        company = self.env.user.company_id
        while not company.chart_template_id and company.parent_id:
            company = company.parent_id
        if not company.vat:
            raise Warning(
                _("Missing VAT number for company %s") % company.name)
        if company.vat[0:2] != 'FR':
            raise Warning(
                _("FEC is for French companies only !"))

        fecfile = StringIO.StringIO()
        w = csv.writer(fecfile, delimiter='|')
        w.writerow(header)

        # INITIAL BALANCE
        unaffected_earnings_xml_ref = self.env.ref('account.data_unaffected_earnings')
        unaffected_earnings_line = True  # used to make sure that we add the unaffected earning initial balance only once
        if unaffected_earnings_xml_ref and self.of_ouv_include:
            # compute the benefit/loss of last year to add in the initial balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        sql_query = """
        SELECT
            %s AS JournalCode,
            %s AS JournalLib,
            %s || ' ' || MIN(aa.name) AS EcritureNum,
            %s AS EcritureDate,
            CASE WHEN aa.code LIKE '455%%' THEN '455000'
                 WHEN aa.internal_type = 'payable' THEN '401000'
                 WHEN aa.internal_type = 'receivable' THEN '411000'
                 ELSE aa.code
            END
            AS CompteNum,
            CASE WHEN aa.code LIKE '455%%' THEN 'Associés'
                 WHEN aa.internal_type = 'payable' THEN 'Fournisseurs'
                 WHEN aa.internal_type = 'receivable' THEN 'Clients'
                 ELSE replace(MIN(aa.name), '|', '/')
            END
            AS CompteLib,
            CASE WHEN aa.internal_type IN ('payable', 'receivable') THEN aa.code
                 ELSE ''
            END
            AS CompAuxNum,
            CASE WHEN aa.internal_type IN ('payable', 'receivable') THEN replace(MIN(aa.name), '|', '/')
                 ELSE ''
            END
            AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' ELSE to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Debit,
            replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Credit,
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
            LEFT JOIN account_account_type aat ON aa.user_type_id = aat.id
        WHERE
            am.company_id = %s
            AND aat.include_initial_balance = 't'
            AND (aml.debit != 0 OR aml.credit != 0)
            AND am.journal_id IN %s
        """
        if self.where_clause_create_date:  # certains client veulent la date de création (exports mensuels vers logiciel compta)
            sql_query += """
            AND am.create_date < %s
            """
        else:
            sql_query += """
            AND am.date < %s
            """

        if self.export_type == 'nonofficial_posted':
            sql_query += """
            AND am.state = 'posted'
            """

        sql_query += """
        GROUP BY aml.account_id, aa.code, aa.internal_type
        HAVING sum(aml.balance) != 0
        ORDER BY CompteNum, aa.code
        """
        formatted_date_from = self.date_from.replace('-', '')

        if self.of_ouv_include:
            self._cr.execute(sql_query, (
                                self.of_ouv_code,
                                self.of_ouv_name,
                                self.of_ouv_name,
                                formatted_date_from,
                                formatted_date_from,
                                formatted_date_from,
                                company.id,
                                self.journal_ids._ids,
                                self.date_from,
                                ))
            for row in self._cr.fetchall():
                listrow = list(row)
                account_id = listrow.pop()
                if not unaffected_earnings_line:
                    account = self.env['account.account'].browse(account_id)
                    if account.user_type_id.id == self.env.ref('account.data_unaffected_earnings').id:
                        # add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
                        unaffected_earnings_line = True
                        current_amount = float(listrow[11].replace(',', '.')) - float(listrow[12].replace(',', '.'))
                        unaffected_earnings_amount = float(unaffected_earnings_results[11].replace(',', '.')) - float(unaffected_earnings_results[12].replace(',', '.'))
                        listrow_amount = current_amount + unaffected_earnings_amount
                        if listrow_amount > 0:
                            listrow[11] = str(listrow_amount).replace('.', ',')
                            listrow[12] = '0,00'
                        else:
                            listrow[11] = '0,00'
                            listrow[12] = str(-listrow_amount).replace('.', ',')
                w.writerow([s.encode("utf-8") for s in listrow])
        # if the unaffected earnings account wasn't in the selection yet: add it manually
        if (not unaffected_earnings_line
            and unaffected_earnings_results
            and (unaffected_earnings_results[11] != '0,00'
                 or unaffected_earnings_results[12] != '0,00')):
            # search an unaffected earnings account
            unaffected_earnings_account = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_unaffected_earnings').id)], limit=1)
            if unaffected_earnings_account:
                unaffected_earnings_results[4] = unaffected_earnings_account.code
                unaffected_earnings_results[5] = unaffected_earnings_account.name
            w.writerow([s.encode("utf-8") for s in unaffected_earnings_results])

        # LINES
        # Il faudra ajouter les comptes de tiers nécessaires au cas par cas (Associés, Fournisseurs, Clients, etc.)
        sql_query = """
        SELECT
            replace(aj.code, '|', '/') AS JournalCode,
            replace(aj.name, '|', '/') AS JournalLib,
            replace(am.name, '|', '/') AS EcritureNum,
            TO_CHAR(am.date, 'YYYYMMDD') AS EcritureDate,
            CASE WHEN aa.code LIKE '455%%' THEN '455000'
                 WHEN aa.internal_type = 'payable' THEN '401000'
                 WHEN aa.internal_type = 'receivable' THEN '411000'
                 ELSE aa.code
            END
            AS CompteNum,
            CASE WHEN aa.code LIKE '455%%' THEN 'Associés'
                 WHEN aa.internal_type = 'payable' THEN 'Fournisseurs'
                 WHEN aa.internal_type = 'receivable' THEN 'Clients'
                 ELSE replace(aa.name, '|', '/')
            END
            AS CompteLib,
            CASE WHEN aa.internal_type IN ('payable', 'receivable') THEN aa.code
                 ELSE ''
            END
            AS CompAuxNum,
            CASE WHEN aa.internal_type IN ('payable', 'receivable') THEN replace(COALESCE(rp.name, ''), '|', '/')
                 ELSE ''
            END
            AS CompAuxLib,
            CASE WHEN am.ref IS null OR am.ref = ''
            THEN '-'
            ELSE replace(am.ref, '|', '/')
            END
            AS PieceRef,
            TO_CHAR(am.date, 'YYYYMMDD') AS PieceDate,
            CASE WHEN aml.name IS NULL THEN '/' ELSE replace(aml.name, '|', '/') END AS EcritureLib,
            replace(CASE WHEN aml.debit = 0 THEN '0,00' ELSE to_char(aml.debit, '000000000000000D99') END, '.', ',') AS Debit,
            replace(CASE WHEN aml.credit = 0 THEN '0,00' ELSE to_char(aml.credit, '000000000000000D99') END, '.', ',') AS Credit,
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
            am.company_id = %s
            AND (aml.debit != 0 OR aml.credit != 0)
            AND am.journal_id IN %s
        """
        if self.where_clause_create_date:  # Certains client veulent la date de création (export mensuel vers logiciel compta).
            sql_query += """
            AND am.create_date >= %s
            AND am.create_date <= %s
            """
        else:
            sql_query += """
            AND am.date >= %s
            AND am.date <= %s
            """

        if self.export_type == 'nonofficial_posted':
            sql_query += """
            AND am.state = 'posted'
            """

        sql_sort = 'am.date, am.name, aml.id'
        if self.sortby == 'sort_journal_partner':
            sql_sort = 'aj.code, rp.name, aml.id'
        sql_query += '\nORDER BY ' + sql_sort

        self._cr.execute(sql_query, (company.id, self.journal_ids._ids, self.date_from, self.date_to))

        for row in self._cr.fetchall():
            listrow = list(row)
            w.writerow([s.encode("utf-8") for s in listrow])

        siren = company.vat[4:13]
        end_date = self.date_to.replace('-', '')
        suffix = '-NONOFFICIAL'
        fecvalue = fecfile.getvalue()
        # venant du fichier est toujours en utf-8
        if self.of_encoding != 'utf-8':
            fecvalue = fecvalue.decode('utf-8').encode(self.of_encoding)
        self.write({
            'fec_data': base64.encodestring(fecvalue),
            'filename': '%sFEC%s%s.%s' % (siren, end_date, suffix, self.of_extension),
            })
        fecfile.close()

        action = {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=account.fr.fec&id=" + str(self.id) + "&filename_field=filename&field=fec_data&download=true&filename=" + self.filename,
            'target': 'self',
            }
        return action
