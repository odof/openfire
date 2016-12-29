# -*- coding: utf-8 -*-

u"""
Pré-requis :
res_company
res_currency

Migration des données comptables, incluant factures, pièces comptables, lettrages

séquences
comptes comptables
journaux
positions fiscales
conditions de règlement
taxes
vendeurs
pièces comptables
lettrages
factures

"""

from openerp import models, api
from main import MAGIC_COLUMNS_VALUES, MAGIC_COLUMNS_TABLES

class import_account(models.AbstractModel):
    _inherit = 'of.migration'

    @api.model
    def import_account_account_type(self):
        """ association des tables account_acount_type.
        Aucune création de ligne n'est effectuée
        """
        cr = self._cr
        # Recuperation des xml_id 9.0
        cr.execute("SELECT TEXTCAT(TEXTCAT(module, '.'), name), res_id FROM ir_model_data WHERE model='account.account.type'")
        data_90 = dict(cr.fetchall())

        # Association des xml_id 6.1 aux ids 9.0
        match_dict = {
            'account.data_account_type_receivable': data_90['account.data_account_type_receivable'],
            'account.data_account_type_payable'   : data_90['account.data_account_type_payable'],
            'account.data_account_type_bank'      : data_90['account.data_account_type_liquidity'],
            'account.data_account_type_cash'      : data_90['account.data_account_type_liquidity'],
            'account.data_account_type_asset'     : data_90['account.data_account_type_current_assets'],
            'account.data_account_type_liability' : data_90['account.data_account_type_current_liabilities'],
            'account.data_account_type_income'    : data_90['account.data_account_type_revenue'],
            'account.data_account_type_expense'   : data_90['account.data_account_type_expenses'],
            'l10n_fr.account_type_immobilisations': data_90['account.data_account_type_current_assets'],
            'l10n_fr.account_type_receivable'     : data_90['account.data_account_type_receivable'],
            'l10n_fr.account_type_payable'        : data_90['account.data_account_type_payable'],
            'l10n_fr.account_type_income'         : data_90['account.data_account_type_revenue'],
            'l10n_fr.account_type_expense'        : data_90['account.data_account_type_expenses'],
            'l10n_fr.account_type_cash'           : data_90['account.data_account_type_liquidity'],
            'l10n_fr.account_type_asset'          : data_90['account.data_account_type_current_assets'],
            'l10n_fr.account_type_equity'         : data_90['account.data_account_type_equity'],
            'l10n_fr.account_type_stocks'         : data_90['account.data_account_type_current_assets'],
            # A retravailler manuellement pour distribuer entre actifs actuels et passif à court terme
            'l10n_fr.account_type_tax'            : data_90['account.data_account_type_current_assets'],

#             'l10n_fr.account_type_dettes'    : 0, # Plusieurs correspondances possibles, matcher les comptes à la main
#             'l10n_fr.account_type_commitment': 0, # Non utilisé dans base openfire
#             'l10n_fr.account_type_special'   : 0, # Non utilisé dans base openfire
        }

        # Remplissage de la table
        cr.execute("SELECT res_id, TEXTCAT(TEXTCAT(module, '.'), name) FROM ir_model_data_61 WHERE model='account.account.type'")
        for id_61, res_id_61 in cr.fetchall():
            id_90 = match_dict.get(res_id_61, False)
            if id_90:
                cr.execute("UPDATE account_account_type_61 SET id_90=%s WHERE id=%s" % (id_90, id_61))

        cr.execute("SELECT name FROM account_account_type_61 WHERE id_90 IS NULL")
        names = [row[0] for row in cr.fetchall()]
        return "%s correspondances manquantes : %s" % (len(names), names)

    @api.model
    def import_account_account(self):
        cr = self._cr

        # Création du lien pour les comptes déjà créés
        cr.execute("UPDATE account_account_61 AS a_61 "
                   "SET id_90 = a.id "
                   "FROM account_account AS a "
                   "INNER JOIN res_company_61 AS c_61 " # company_id est non nul en 6.1 et en 9.0
                   "  ON c_61.id_90 = a.company_id "
                   "WHERE c_61.id = a_61.company_id "
                   "  AND (a_61.code = a.code "
                   "    OR SUBSTRING(a_61.code FROM 1 FOR 6) = a.code)") # Comptes a 6 chiffres en 9.0

        # Creation des comptes comptables manquants
        fields_90 = ['code', 'reconcile', 'currency_id', 'user_type_id', 'name', 'company_id', 'note', 'internal_type']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'currency_id'  : 'cur.id_90',
            'user_type_id' : 't.id_90',
            'company_id'   : 'comp.id_90',
            'internal_type': 'tab.type',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_account_61', False, False, False),
            ('cur', 'res_currency_61', 'id', 'tab', 'currency_id'),
            ('t', 'account_account_type_61', 'id', 'tab', 'user_type'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        where_clause = "tab.type != 'view' AND tab.id_90 IS NULL"

        self.insert_values('account.account', values, tables, where_clause=where_clause)

        # Création du lien pour les comptes nouvellement créés
        cr.execute("UPDATE account_account_61 AS a_61\n"
                   "SET id_90 = a.id\n"
                   "FROM account_account AS a\n"
                   "INNER JOIN res_company_61 AS c_61\n"
                   "  ON c_61.id_90 = a.company_id\n"
                   "WHERE a_61.id_90 IS NULL\n"
                   "  AND c_61.id = a_61.company_id\n"
                   "  AND a_61.code = a.code")

        # Mise à jour des libellés des comptes, et des codes pour le cas des comptes à 6 chiffres
        cr.execute("UPDATE account_account AS a\n"
                   "SET name = a_61.name, code = a_61.code\n"
                   "FROM account_account_61 AS a_61\n"
                   "WHERE a_61.id_90 = a.id\n"
                   "  AND (a_61.name != a.name"
                   "    OR a_61.code != a.code)")

    @api.model
    def import_account_analytic_account(self):
        #@todo: A migrer, il existe 3 comptes dans openfire, mais non utilisés
        # Migrer aussi account_analytic_line, etc.
        pass

    @api.model
    def import_account_journal(self):
        cr = self._cr

        # On efface les journaux 9.0, inutiles
        cr.execute("DELETE FROM of_account_payment_mode")
        cr.execute("DELETE FROM account_journal")
        cr.execute("SELECT setval('account_journal_id_seq', 1, 'f')")

        # Migration des journaux 6.1
        fields_90 = ['name', 'default_debit_account_id', 'default_credit_account_id', 'code', 'sequence_id', 'currency_id',
                     'company_id', 'type', 'group_invoice_lines', 'update_posted']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'default_debit_account_id' : 'acc_deb.id_90',
            'default_credit_account_id': 'acc_cred.id_90',
            'sequence_id'              : 'seq.id_90',
            'currency_id'              : 'cur.id_90',
            'company_id'               : 'comp.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_journal_61', False, False, False),
            ('acc_deb', 'account_account_61', 'id', 'tab', 'default_debit_account_id'),
            ('acc_cred', 'account_account_61', 'id', 'tab', 'default_credit_account_id'),
            ('seq', 'ir_sequence_61', 'id', 'tab', 'sequence_id'),
            ('cur', 'res_currency_61', 'id', 'tab', 'currency'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.journal', values, tables)

        # Création du lien
        cr.execute("UPDATE account_journal_61 AS j_61 "
                   "SET id_90 = j.id "
                   "FROM account_journal AS j "
                   "INNER JOIN res_company_61 AS c_61 "
                   "  ON c_61.id_90 = j.company_id "
                   "WHERE c_61.id = j_61.company_id "
                   "  AND j_61.code = j.code")

        # Table account_journal_type_rel
        self.map_relation_field('account.journal', 'type_control_ids')

    @api.model
    def import_account_tax(self):
        cr = self._cr

        # On efface les taxes 9.0, inutiles
        cr.execute("DELETE FROM account_tax")
        cr.execute("SELECT setval('account_tax_id_seq', 1, 'f')")
        cr.execute("UPDATE account_tax_61 SET id_90 = nextval('account_tax_id_seq') WHERE id_90 IS NULL")

        # Migration des taxes 6.1
        fields_90 = ['amount_type', 'account_id', 'name', 'sequence', 'tax_group_id', 'company_id', 'type_tax_use', 'analytic',
                     'amount', 'include_base_amount', 'price_include', 'active', 'refund_account_id', 'description']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'               : 'tab.id_90',
            'amount_type'      : "tab.type",
            'account_id'       : 'account.id_90',
            'tax_group_id'     : '1',
            'company_id'       : 'comp.id_90',
            'analytic'         : "'f'",
            'amount'           : '100 * tab.amount', # En considerant que le type est toujours 'percent'
            'refund_account_id': 'acc_ref.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_tax_61', False, False, False),
            ('account', 'account_account_61', 'id', 'tab', 'account_collected_id'),
            ('acc_ref', 'account_account_61', 'id', 'tab', 'account_paid_id'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.tax', values, tables)

        # Creation des étiquettes manquantes
        cr.execute("INSERT INTO account_account_tag(create_uid, create_date, applicability, name)\n"
                   "SELECT create_uid, create_date, 'taxes', description\n"
                   "FROM account_tax\n"
                   "WHERE description NOT IN (SELECT name FROM account_account_tag WHERE applicability='taxes')")

        # Creation des liens taxe-étiquette
        cr.execute("INSERT INTO account_tax_account_tag(account_tax_id, account_account_tag_id)\n"
                   "SELECT tax.id, tag.id\n"
                   "FROM account_tax AS tax INNER JOIN account_account_tag AS tag ON tax.description=tag.name")
        
        # Table account_account_tax_default_rel
        self.map_relation_field('account.account', 'tax_ids')
        # Table product_taxes_rel
        self.map_relation_field('product.template', 'taxes_id')
        # Table product_supplier_taxes_rel
        self.map_relation_field('product.template', 'supplier_taxes_id')

    @api.model
    def import_account_bank_statement(self):
        cr = self._cr

        # Association des account_bank_statement_61 aux nouveaux account_bank_statement 9.0
        cr.execute("UPDATE account_bank_statement_61 SET id_90 = nextval('account_bank_statement_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['user_id', 'journal_id', 'company_id', 'difference', 'state', 'balance_end', 'balance_start', 'date',
                     'balance_end_real', 'name', 'total_entry_encoding', 'date_done']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'        : 'tab.id_90',
            'user_id'   : 'users.id_90',
            'journal_id': 'journal.id_90',
            'company_id': 'comp.id_90',
            'date_done' : 'tab.closing_date',
            'difference': 'tab.balance_end_real - tab.balance_end',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_bank_statement_61', False, False, False),
            ('users', 'res_users_61', 'id', 'tab', 'user_id'),
            ('journal', 'account_journal_61', 'id', 'tab', 'journal_id'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.bank.statement', values, tables)

    @api.model
    def import_account_bank_statement_line(self):
        cr = self._cr

        # Association des account_bank_statement_61 aux nouveaux account_bank_statement 9.0
        cr.execute("UPDATE account_bank_statement_line_61 SET id_90 = nextval('account_bank_statement_line_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['statement_id', 'partner_id', 'account_id', 'company_id', 'journal_id', 'partner_name', 'ref', 'sequence',
                     'name', 'note', 'amount', 'date']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'             : 'tab.id_90',
            'statement_id'   : 'statement.id_90',
            'partner_id'     : 'partner.id_90',
            'account_id'     : 'account.id_90',
            'company_id'     : 'comp.id_90',
            'partner_name'   : 'partner.name',
            'journal_id'     : 'journal.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_bank_statement_line_61', False, False, False),
            ('statement', 'account_bank_statement_61', 'id', 'tab', 'statement_id'),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('account', 'account_account_61', 'id', 'tab', 'account_id'),
            ('comp', 'res_company_61', 'id', 'statement', 'company_id'),
            ('journal', 'account_journal_61', 'id', 'statement', 'journal_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.bank.statement.line', values, tables)

    @api.model
    def import_payment_mode(self):
        cr = self._cr

        # Suppression des modes de paiements existants (générés automatiquement depuis les journaux)
        cr.execute("DELETE FROM of_account_payment_mode")
        cr.execute("SELECT setval('of_account_payment_mode_id_seq', 1, 'f')")

        # Association des payment_mode_61 aux of_account_payment_mode 9.0
        cr.execute("UPDATE payment_mode_61 SET id_90 = nextval('of_account_payment_mode_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['name', 'partner_id', 'company_id', 'journal_id']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'        : 'tab.id_90',
            'partner_id': 'partner.id_90',
            'company_id': 'comp.id_90',
            'journal_id': 'journal.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'payment_mode_61', False, False, False),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
            ('journal', 'account_journal_61', 'id', 'tab', 'journal'),
            ('bank', 'res_partner_bank_61', 'id', 'tab', 'bank_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('of.account.payment.mode', values, tables)

    @api.model
    def import_account_move(self):
        cr = self._cr

        # Association des account_move_61 aux nouveaux account_move 9.0
        cr.execute("UPDATE account_move_61 SET id_90 = nextval('account_move_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['ref', 'company_id', 'currency_id', 'journal_id', 'state',
                     'narration', 'date', 'amount', 'partner_id', 'name']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'             : 'tab.id_90',
            'company_id'     : 'comp.id_90',
            'currency_id'    : 'cur.id_90',
            'journal_id'     : 'journal.id_90',
            'partner_id'     : 'partner.id_90',
            'amount'         : 'sum_line.debit', # Laisser un espace avant line.debit pour la détection de la table par insert_values()
        })
        values.update(MAGIC_COLUMNS_VALUES)

        sum_line_table = "(SELECT move_id, SUM(debit) AS debit FROM account_move_line GROUP BY move_id)"

        tables = [
            ('tab', 'account_move_61', False, False, False),
            ('journal', 'account_journal_61', 'id', 'tab', 'journal_id'),
            ('comp', 'res_company_61', 'id', 'journal', 'company_id'),
            ('cur', 'res_currency_61', 'id', 'comp', 'currency_id'),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('sum_line', sum_line_table, 'move_id', 'tab', 'id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.move', values, tables)

        # Manquent les champs calculés en fonction des lettrages : matched_percentage

    @api.model
    def import_of_voucher_remise(self):
        cr = self._cr

        # Association des of_voucher_remise aux OfAccountPaymentBankDeposit 9.0
        cr.execute("UPDATE of_voucher_remise_61 SET id_90 = nextval('of_account_payment_bank_deposit_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['name', 'date', 'state', 'move_id', 'journal_id']

        values = {field: "tab."+field for field in fields_90}

        values.update({
            'id'        : 'tab.id_90',
            'state'     : "'posted'",
            'move_id'   : 'move.id_90',
            'journal_id': 'journal.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        #@todo: Si certaines remises en banque de la 6.1 n'ont pas de pièce comptable associée,
        #   on pourra générer un script python pour retrouver la pièce comptable grâce au lettrage des paiements.

        tables = [
            ('tab', 'of_voucher_remise_61', False, False, False),
            ('move', 'account_move_61', 'id', 'tab', 'move_id'),
            ('journal', 'account_journal_61', 'id', 'move', 'journal_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('of.account.payment.bank.deposit', values, tables)

    @api.model
    def import_account_voucher(self):
        cr = self._cr

        # Association des account_voucher_61 aux nouveaux account_voucher 9.0
        cr.execute("UPDATE account_voucher_61 SET id_90 = nextval('account_payment_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['communication', 'currency_id', 'partner_id', 'payment_method_id', 'payment_difference_handling',
                     'company_id', 'state', 'writeoff_account_id', 'payment_date', 'partner_type', 'name',
                     'destination_journal_id', 'journal_id', 'amount', 'payment_type', 'payment_reference','of_deposit_id']

        values = {field: "tab."+field for field in fields_90}

        cr.execute("SELECT payment_type,id FROM account_payment_method")
        payment_methods = dict(cr.fetchall())

        values.update({
            'id'                         : 'tab.id_90',
            'communication'              : 'tab.name',
            'currency_id'                : 'cur.id_90',
            'partner_id'                 : 'partner.id_90',
            'payment_method_id'          : "CASE WHEN tab.type IN ('purchase','payment') THEN %(outbound)s ELSE %(inbound)s END" % payment_methods,
            'payment_difference_handling': "CASE WHEN tab.payment_option = 'without_writeoff' THEN 'open' ELSE 'reconcile' END",
            'company_id'                 : 'comp.id_90',
            'writeoff_account_id'        : 'writeoff_acc_id.id_90',
            'payment_date'               : 'tab.date',
            'partner_type'               : "CASE WHEN tab.type IN ('purchase','payment') THEN 'supplier' ELSE 'customer' END",
            'name'                       : 'tab.number',
            'destination_journal_id'     : 'NULL',
            'of_payment_mode_id'         : 'mode.id_90',
            'journal_id'                 : 'journal.id_90',
            'payment_type'               : "CASE WHEN tab.type IN ('purchase','payment') THEN 'outbound' ELSE 'inbound' END",
            'payment_reference'          : 'tab.reference',
            'of_deposit_id'              : 'remise.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_voucher_61', False, False, False),
            ('mode', 'payment_mode_61', 'id', 'tab', 'mode_id'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
            ('cur', 'res_currency_61', 'id', 'comp', 'currency_id'), # Normalement ce devrait être journal.currency, mais ne doit pas être NULL
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('journal', 'account_journal_61', 'id', 'mode', 'journal'),
            ('writeoff_acc_id', 'account_account_61', 'id', 'tab', 'writeoff_acc_id'),
            ('remise', 'of_voucher_remise_61', 'id', 'tab', 'remise_id'),
        ] + MAGIC_COLUMNS_TABLES

        where_clause = "tab.state != 'cancel'" # L'état cancel n'existe pas pour les paiements v9.0
        self.insert_values('account.payment', values, tables, where_clause)

    @api.model
    def import_account_payment_term(self):
        cr = self._cr

        cr.execute("SELECT TEXTCAT(TEXTCAT(module, '.'), name), res_id FROM ir_model_data WHERE model='account.payment.term'")
        data_90 = dict(cr.fetchall())

        # Association des xml_id 6.1 aux ids 9.0
        match_dict = {
#            'of_mode_paiement.account_payment_term_facture': data_90['account.account_payment_term_immediate'],
            'account.account_payment_term_net'             : data_90['account.account_payment_term_net'],
        }

        # Remplissage de la table
        cr.execute("SELECT res_id, TEXTCAT(TEXTCAT(module, '.'), name) FROM ir_model_data_61 WHERE model='account.payment.term'")
        for id_61, res_id_61 in cr.fetchall():
            id_90 = match_dict.get(res_id_61, False)
            if id_90:
                cr.execute("UPDATE account_account_type_61 SET id_90=%s WHERE id=%s" % (id_90, id_61))

        # Désactivation des conditions de règlement Odoo sans correspondance
        cr.execute("UPDATE account_payment_term AS t SET active='f'\n"
                   "WHERE id NOT IN (SELECT id_90 FROM account_payment_term_61 WHERE id_90 IS NOT NULL)")

        # Association des account_payment_term_61 aux nouveaux account_payment_term 9.0
        cr.execute("UPDATE account_payment_term_61 SET id_90 = nextval('account_payment_term_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['name', 'company_id', 'note', 'active', 'imp_facture', 'of_arrondi']

        cr.execute('SELECT id FROM res_company WHERE parent_id IS NULL LIMIT 1')
        company_id = cr.fetchone()[0]

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'        : 'tab.id_90',
            'company_id': str(company_id),
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_payment_term_61', False, False, False),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.payment.term', values, tables)

    @api.model
    def import_account_payment_term_line_old(self):
        def get_next_id():
            cr.execute("SELECT nextval('account_payment_term_line_id_seq')")
            return cr.fetchall()[0][0]
        cr = self._cr

        # Correspondance des lignes existantes
        # Les paiements enregistrés par défaut n'ont qu'une seule ligne d'échéance
        cr.execute("UPDATE account_payment_term_line_61 AS l61\n"
                   "SET id_90 = l90.id\n"
                   "FROM account_payment_term_line AS l90\n"
                   "INNER JOIN account_payment_term_61 AS t61 ON t61.id_90=l90.payment_id\n"
                   "WHERE l61.payment_id=t61.id")

        # Association des account_payment_term_line_61 aux nouveaux account_payment_term_line 9.0
#         cr.execute("UPDATE account_payment_term_line_61 SET id_90 = nextval('account_payment_term_line_id_seq') WHERE id_90 IS NULL")


        fields_61 = ['name', 'value_amount', 'sequence', 'days2', 'days', 'value', 'of_mois']
        fields_61 = ['id_90'] + MAGIC_COLUMNS_VALUES.keys() + fields_61

        select_query = ("SELECT id,%s \n"
                        "FROM account_payment_term_line_61\n"
                        "WHERE payment_id = %%s\n"
                        "ORDER BY sequence") % ",".join(fields_61)

        fields_90 = ['payment_id', 'option', 'sequence', 'days', 'value', 'value_amount', 'months']#, 'payment_days', 'amount_round', 'weeks']
        fields_90 = ['id'] + MAGIC_COLUMNS_VALUES.keys() + fields_90 

        common_fields = [field for field in fields_61 if field in fields_90]

#         insert_query = ("INSERT INTO account_payment_term_line(%s)"
#                         "VALUES (%%s)") % ",".join(fields_90)

        insert_query = ("INSERT INTO account_payment_term_line(%s)\n"
                        "SELECT %%s\n"
                        "FROM account_payment_term_line_61 AS l61\n"
                        "WHERE l61.id = %%s") % ",".join(fields_90)

        cr.execute("SELECT id, id_90 FROM account_payment_term_61\n"
                   "WHERE id IN (SELECT payment_id FROM account_payment_term_line_61 WHERE id_90 IS NULL)")

        for payment_id, payment_id_90 in cr.fetchall():
            cr.execute(select_query % payment_id)
#             vals = [dict(zip(fields_61, row)) for row in cr.fetchall()]
            vals = cr.dictfetchall()

            sequential_lines = False
            for line_data in vals:
                if line_data['days2'] and line_data['days']:
                    sequential_lines = True
                    cr.execute("UPDATE account_payment_term SET sequential_lines='t' WHERE id = %s" % payment_id_90)
                    break

            line_prec = {}
            for line_data in vals:
                create_data = {field: 'l61.%s' % field for field in common_fields}
                create_data.update({
#                     'id': line_data['id_90'],
                    'payment_id': payment_id_90,
                    'months': 'l61.of_mois',
                    'option': "'day_after_invoice_date'",
                })
                # Manquants : option
                if sequential_lines:
                    # Calculer la(les) ligne(s) suivante(s) en fonction de line_prec
                    days = line_data['days'] - line_prec.get('days', 0)
                    if line_data['days2'] and days:
                        sequence = line_data['sequence']
                        if line_prec:
                            sequence = (sequence + line_prec['sequence'] + 1) / 2
                        else:
                            sequence -= 1
                        preline_data = dict(create_data, id=get_next_id(), sequence=sequence)

                        cr.execute(insert_query % (",".join(str(preline_data[field]) for field in fields_90), line_data['id']))

                        create_data.update({
                            'days': '0',
                            'months': '0',
                        })
                    line_prec = line_data

                if line_data['days2'] == -1:
                    create_data['option'] = "'last_day_current_month'"
                elif line_data['days2']:
                    create_data['option'] = "'fix_day_following_month'"
                    create_data['days'] = 'l61.days2'
                create_data['id'] = get_next_id()
                cr.execute(insert_query % (",".join(str(create_data[field]) for field in fields_90), line_data['id']))
                cr.execute("UPDATE account_payment_term_line_61 AS l61\n"
                           "SET id_90 = %s\n"
                           "WHERE l61.id=%s" % (create_data['id'], line_data['id']))

    @api.model
    def import_account_payment_term_line(self):
        def get_next_id():
            cr.execute("SELECT nextval('account_payment_term_line_id_seq')")
            return str(cr.fetchall()[0][0])
        cr = self._cr

        # Correspondance des lignes existantes
        # Les paiements enregistrés par défaut n'ont qu'une seule ligne d'échéance
        cr.execute("UPDATE account_payment_term_line_61 AS l61\n"
                   "SET id_90 = l90.id\n"
                   "FROM account_payment_term_line AS l90\n"
                   "INNER JOIN account_payment_term_61 AS t61 ON t61.id_90=l90.payment_id\n"
                   "WHERE l61.payment_id=t61.id")

        fields_61 = ['name', 'value_amount', 'sequence', 'days2', 'days', 'value', 'of_mois']
        fields_61 = ['id_90'] + MAGIC_COLUMNS_VALUES.keys() + fields_61

        select_query = ("SELECT id,%s \n"
                        "FROM account_payment_term_line_61\n"
                        "WHERE payment_id = %%s\n"
                        "ORDER BY sequence") % ",".join(fields_61)

        fields_90 = ['payment_id', 'option', 'sequence', 'days', 'value', 'value_amount', 'months']#, 'payment_days', 'amount_round', 'weeks']
        fields_90 = ['id'] + MAGIC_COLUMNS_VALUES.keys() + fields_90 

        values = {field: "tab."+field for field in fields_90}
        values.update({
#             'months': 'tab.of_mois',
            'option': "'day_after_invoice_date'",
            'days2' : 0,
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_payment_term_line_61', False, False, False),
            ('payment', 'account_payment_term_61', 'id', 'tab', 'payment_id'),
        ] + MAGIC_COLUMNS_TABLES

        where_clause = "tab.id = %s"

        cr.execute("SELECT id, id_90 FROM account_payment_term_61\n"
                   "WHERE id IN (SELECT payment_id FROM account_payment_term_line_61 WHERE id_90 IS NULL)")

        for payment_id, payment_id_90 in cr.fetchall():
            cr.execute(select_query % payment_id)
            vals = cr.dictfetchall()

            # Calcul du paramètre sequential_lines à attribuer aux conditions de règlement en fonction de leurs lignes
            sequential_lines = False
            for line_data in vals:
                if line_data['days2'] and line_data['days']:
                    sequential_lines = True
                    cr.execute("UPDATE account_payment_term SET sequential_lines='t' WHERE id = %s" % payment_id_90)
                    break

            # Calcul des lignes, différent en fonction du paramètre sequential_lines
            line_prec = {}
            values['payment_id'] = str(payment_id_90)
            for line_data in vals:
                values.update({
                    'id': get_next_id(),
                    'days': 'tab.days',
                    'months': 'tab.of_mois',
                })

                if sequential_lines:
                    # Calculer la(les) ligne(s) suivante(s) en fonction de line_prec
                    days = line_data['days'] - line_prec.get('days', 0)
                    months = line_data['of_mois'] - line_prec.get('of_mois', 0)
                    if line_data['days2'] and days:
                        sequence = line_data['sequence']
                        if line_prec:
                            sequence = (sequence + line_prec['sequence'] + 1) / 2
                        else:
                            sequence -= 1

                        preline_data = dict(values, sequence=str(sequence), value="'fixed'", value_amount='0',
                                            days=str(days), months=str(months))
                        self.insert_values('account.payment.term.line', preline_data, tables, where_clause=where_clause % line_data['id'])

                        values.update({
                            'id': get_next_id(),
                            'days': '0',
                            'months': '0',
                        })
                    else:
                        values.update({
                            'days': str(days),
                            'months': str(months),
                        })
                    line_prec = line_data

                if line_data['days2'] == -1:
                    values['option'] = "'last_day_current_month'"
                elif line_data['days2']:
                    values['option'] = "'fix_day_following_month'"
                    values['days'] = 'tab.days2'
                else:
                    values['option'] = "'day_after_invoice_date'"

                self.insert_values('account.payment.term.line', values, tables, where_clause=where_clause % line_data['id'])
                cr.execute("UPDATE account_payment_term_line_61 AS l61\n"
                           "SET id_90 = %s\n"
                           "WHERE l61.id=%s" % (values['id'], line_data['id']))

    @api.model
    def import_account_fiscal_position(self):
        cr = self._cr

        # Association des account_fiscal_position_61 aux nouveaux account_fiscal_position 9.0
        cr.execute("UPDATE account_fiscal_position_61 SET id_90 = nextval('account_fiscal_position_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['name', 'company_id', 'note', 'active']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'             : 'tab.id_90',
            'company_id'     : 'comp.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_fiscal_position_61', False, False, False),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.fiscal.position', values, tables)

    @api.model
    def import_account_fiscal_position_tax(self):
        cr = self._cr

        # Association des account_fiscal_position_tax_61 aux nouveaux account_fiscal_position_tax 9.0
        cr.execute("UPDATE account_fiscal_position_tax_61 SET id_90 = nextval('account_fiscal_position_tax_id_seq') WHERE id_90 IS NULL")

        values = {
            'id'         : 'tab.id_90',
            'position_id': 'position.id_90',
            'tax_src_id' : 'tax_src.id_90',
            'tax_dest_id': 'tax_dest.id_90',
        }
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_fiscal_position_tax_61', False, False, False),
            ('position', 'account_fiscal_position_61', 'id', 'tab', 'position_id'),
            ('tax_src', 'account_tax_61', 'id', 'tab', 'tax_src_id'),
            ('tax_dest', 'account_tax_61', 'id', 'tab', 'tax_dest_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.fiscal.position.tax', values, tables)

    @api.model
    def import_account_fiscal_position_account(self):
        cr = self._cr

        # Association des account_fiscal_position_account_61 aux nouveaux account_fiscal_position_account 9.0
        cr.execute("UPDATE account_fiscal_position_account_61 SET id_90 = nextval('account_fiscal_position_account_id_seq') WHERE id_90 IS NULL")

        values = {
            'id'             : 'tab.id_90',
            'position_id'    : 'position.id_90',
            'account_src_id' : 'account_src.id_90',
            'account_dest_id': 'account_dest.id_90',
        }
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_fiscal_position_account_61', False, False, False),
            ('position', 'account_fiscal_position_61', 'id', 'tab', 'position_id'),
            ('account_src', 'account_account_61', 'id', 'tab', 'account_src_id'),
            ('account_dest', 'account_account_61', 'id', 'tab', 'account_dest_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.fiscal.position.account', values, tables)

    @api.model
    def import_account_invoice(self):
        cr = self._cr

        # Association des account_bank_statement_61 aux nouveaux account_bank_statement 9.0
        cr.execute("UPDATE account_invoice_61 SET id_90 = nextval('account_invoice_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['comment', 'date_due', 'reference', 'reference_type', 'number', 'journal_id', 'currency_id',
                     'partner_id', 'amount_untaxed', 'partner_bank_id', 'company_id', 'amount_tax', 'state',
                     'fiscal_position_id', 'type', 'account_id', 'reconciled', 'origin', 'residual', 'move_name',
                     'date_invoice', 'payment_term_id', 'user_id', 'move_id', 'amount_total', 'name', 'commercial_partner_id']

        values = {field: "tab."+field for field in fields_90}
        # Commencer la valeur par un espace blanc pour ne pas que 'CASE' soit interprété comme un nom de table par insert_values() !
        signed_case = lambda field: "CASE WHEN tab.type IN ('in_refund', 'out_refund') THEN -%s ELSE %s END" % (field, field)
        values.update({
            'id'                   : 'tab.id_90',
            'journal_id'           : 'journal.id_90',
            'currency_id'          : 'currency.id_90',
            'partner_id'           : 'partner.id_90',
            'commercial_partner_id': 'partner_90.commercial_partner_id',
            'partner_bank_id'      : 'bank.id_90',
            'company_id'           : 'COALESCE( shop.id_90, comp.id_90)',
            'fiscal_position_id'   : 'fpos.id_90',
            'account_id'           : 'account.id_90',
            'payment_term_id'      : 'pterm.id_90',
            'user_id'              : 'users.id_90',
            'move_id'              : 'move.id_90',
            'reference_type'       : "'none'",
            'move_name'            : 'tab.internal_number',

            'amount_total_signed'        : signed_case('tab.amount_total'),
            'amount_untaxed_signed'      : signed_case('tab.amount_untaxed'),
            'residual_signed'            : signed_case('tab.residual'),

            # On considère que la monnaie de la société est la même que celle de la facture
            'amount_total_company_signed': signed_case('tab.amount_total'),
            'residual_company_signed'    : signed_case('tab.residual'),
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_invoice_61', False, False, False),
            ('journal', 'account_journal_61', 'id', 'tab', 'journal_id'),
            ('currency', 'res_currency_61', 'id', 'tab', 'currency_id'),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('partner_90', 'res_partner', 'id', 'partner', 'id_90'),
            ('bank', 'res_partner_bank_61', 'id', 'tab', 'partner_bank_id'),
            ('shop', 'sale_shop_61', 'id', 'tab', 'sale_maga'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
            ('fpos', 'account_fiscal_position_61', 'id', 'tab', 'fiscal_position'),
            ('account', 'account_account_61', 'id', 'tab', 'account_id'),
            ('pterm', 'account_payment_term_61', 'id', 'tab', 'payment_term'),
            ('users', 'res_users_61', 'id', 'tab', 'user_id'),
            ('move', 'account_move_61', 'id', 'tab', 'move_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.invoice', values, tables)

    @api.model
    def import_account_invoice_line(self):
        cr = self._cr

        # Association des account_bank_statement_61 aux nouveaux account_bank_statement 9.0
        cr.execute("UPDATE account_invoice_line_61 SET id_90 = nextval('account_invoice_line_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['origin', 'sequence', 'price_unit', 'price_subtotal', 'uom_id', 'partner_id',# 'currency_id',
                     'invoice_id', 'company_id', 'account_id', 'discount', 'name', 'product_id', 'account_analytic_id',
                     'quantity', 'price_subtotal_signed']

        values = {field: "tab."+field for field in fields_90}
        # Commencer la valeur par un espace blanc pour ne pas que 'CASE' soit interprété comme un nom de table par insert_values() !
        signed_case = lambda field: "CASE WHEN inv.type IN ('in_refund', 'out_refund') THEN -%s ELSE %s END" % (field, field)
        values.update({
            'id'                   : 'tab.id_90',
            'uom_id'               : 'uom.id_90',
            'partner_id'           : 'partner.id_90',
            'invoice_id'           : 'inv.id_90',
            'company_id'           : 'inv_90.company_id',
            'account_analytic_id'  : 'account_analytic.id_90',
            'account_id'           : 'account.id_90',
            'product_id'           : 'product.id_90',
            'price_subtotal_signed': signed_case('tab.price_subtotal'),
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_invoice_line_61', False, False, False),
            ('currency', 'res_currency_61', 'id', 'tab', 'currency_id'),
            ('uom', 'product_uom_61', 'id', 'tab', 'uos_id'),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('inv', 'account_invoice_61', 'id', 'tab', 'invoice_id'),
            ('inv_90', 'account_invoice', 'id', 'inv', 'id_90'),
            ('account_analytic', 'account_analytic_account_61', 'id', 'tab', 'account_analytic_id'),
            ('account', 'account_account_61', 'id', 'tab', 'account_id'),
            ('product', 'product_product_61', 'id', 'tab', 'product_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.invoice.line', values, tables)

    @api.model
    def import_account_move_line(self):
        cr = self._cr

        # Association des account_bank_statement_61 aux nouveaux account_bank_statement 9.0
        cr.execute("UPDATE account_move_line_61 SET id_90 = nextval('account_move_line_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['statement_id', 'account_id', 'company_id', 'currency_id', 'date_maturity', 'user_type_id', 'partner_id',
                     'blocked', 'analytic_account_id', 'credit', 'journal_id', 'amount_residual_currency', 'debit', 'ref',
                     'reconciled', 'date', 'move_id', 'name', 'payment_id', 'company_currency_id', 'balance', 'product_id',
                     'invoice_id', 'amount_residual', 'product_uom_id', 'amount_currency', 'quantity']# , 'tax_line_id'

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'                      : 'tab.id_90',
            'statement_id'            : 'statement.id_90',
            'account_id'              : 'account.id_90',
            'company_id'              : 'comp.id_90',
            'currency_id'             : 'cur.id_90', # Vaut NULL normalement
            'date_maturity'           : 'COALESCE( tab.date_maturity, tab.date)',
            'user_type_id'            : 'user_type.id_90',
            'partner_id'              : 'partner.id_90',
            'analytic_account_id'     : 'analytic_account.id_90', # Vaut NULL dans la plupart des bases (sauf campistro)
            'journal_id'              : 'journal.id_90',
            'amount_residual_currency': '0.0', #@todo: A calculer pour le cas où currency_id ne vaut pas NULL
            'reconciled'              : "'f'", # Calculé dans import_account_move_reconcile
            'move_id'                 : 'move.id_90',
            'payment_id'              : 'voucher.id_90',
            'company_currency_id'     : 'company_currency.id_90',
            'balance'                 : 'tab.debit - tab.credit',
            'product_id'              : 'product.id_90',
            'amount_residual'         : '0', # Calculé dans import_account_move_reconcile
            'product_uom_id'          : 'product_uom.id_90',
            'invoice_id'              : 'invoice.id_90',
#             'tax_line_id'             : 'CASE WHEN tab.credit = 0 THEN credit_tax.id_90 ELSE debit_tax.id_90 END',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'account_move_line_61', False, False, False),
            ('statement', 'account_bank_statement_61', 'id', 'tab', 'statement_id'),
            ('account', 'account_account_61', 'id', 'tab', 'account_id'),
            ('cur', 'res_currency_61', 'id', 'tab', 'currency_id'), # Vaut NULL normalement
            ('user_type', 'account_account_type_61', 'id', 'account', 'user_type'),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('analytic_account', 'account_analytic_account_61', 'id', 'tab', 'analytic_account_id'),
            ('move', 'account_move_61', 'id', 'tab', 'move_id'),
            ('journal', 'account_journal_61', 'id', 'move', 'journal_id'),
            ('comp', 'res_company_61', 'id', 'journal', 'company_id'),
            ('company_currency', 'res_currency_61', 'id', 'comp', 'currency_id'),
            ('product', 'product_product_61', 'id', 'tab', 'product_id'),
            ('product_uom', 'product_uom_61', 'id', 'tab', 'product_uom_id'),
#             ('credit_tax', 'account_tax_61', 'id', 'tab', 'account_tax_id'),
#             ('credit_tax', 'account_tax_61', 'id', 'tab', 'account_tax_id'),
            ('voucher', 'account_voucher_61', 'move_id', 'tab', 'account_id'),
            ('invoice', 'account_invoice_61', 'move_id', 'tab', 'account_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('account.move.line', values, tables)

        # Remplissage séparé du champ tax_line_id séparé (pour éviter des lignes doublon si plusieurs taxes avec même compte)
        cr.execute("""
UPDATE account_move_line AS line
SET tax_line_id = tax.id
FROM account_tax AS tax
WHERE tax.active
  AND (   (line.debit=0 AND line.account_id=tax.account_id)
       OR (line.credit=0 AND line.account_id=tax.refund_account_id))
""")

        # Table account_move_line_account_tax_rel
        #  - Pour les lignes dont taxe_code_id est défini, on matche sur le base_code_id ou ref_base_code_id de la taxe
        cr.execute("""
INSERT INTO account_move_line_account_tax_rel(account_move_line_id, account_tax_id)
SELECT line61.id_90, tax61.id_90
FROM account_move_line_61 AS line61
LEFT JOIN account_tax_61 AS tax61
  ON line61.tax_code_id IN (tax61.base_code_id, tax61.ref_base_code_id)
WHERE line61.tax_code_id IS NOT NULL
  AND tax61.active
""")
        #  - Pour les lignes dont taxe_code_id n'est pas défini, on récupère les taxes des autres lignes
        cr.execute("""
INSERT INTO account_move_line_account_tax_rel(account_move_line_id, account_tax_id)
SELECT DISTINCT line.id, line2.tax_line_id
FROM account_move_line_61 AS line61
INNER JOIN account_move_line AS line
  ON line.id=line61.id_90
INNER JOIN account_move_line AS line2
  ON line2.move_id = line.move_id
WHERE line61.tax_code_id IS NULL
  AND line2.tax_line_id IS NOT NULL
  AND (line2.credit=0) = (line.credit=0)
""")

        # Manquent les champs calculés en fonction des lettrages : debit_cash_basis, credit_cash_basis, balance_cash_basis

        # Table account_invoice_account_move_line_rel, migration custom car champ calculé non sauvegardé en v6.1
        # invoice.payment_ids -> invoice.payment_move_line_ids
        cr.execute("""
INSERT INTO account_invoice_account_move_line_rel(account_invoice_id, account_move_line_id)
SELECT i.id, matched_line.id2
FROM account_invoice AS i
INNER JOIN account_move AS m ON m.id = i.move_id
INNER JOIN account_move_line AS ml ON ml.move_id = m.id
INNER JOIN (
  SELECT debit_move_id AS id1, credit_move_id AS id2
  FROM account_partial_reconcile
  UNION
  SELECT credit_move_id AS id1, debit_move_id AS id2
  FROM account_partial_reconcile
) AS matched_line ON matched_line.id1=ml.id
""")

    @api.model
    def import_account_move_reconcile(self):
        def create_reconcile(cr, rows):
            while rows[0] and rows[1]:
                debit_line = rows[0].pop()
                credit_line = rows[1].pop()

                amount = min(credit_line[2], -debit_line[2])

                if amount: # Pour éviter les écriture à 0
                    credit_line[2] = round(credit_line[2] - amount, 2)
                    debit_line[2] = round(debit_line[2] + amount, 2)

                    # Création du rapprochement
                    cr.execute("INSERT INTO account_partial_reconcile(create_uid, create_date, credit_move_id, company_id, amount, debit_move_id)\n"
                               "VALUES (%s, %s, %s, %s, %s, %s)", (debit_line[3], debit_line[4], credit_line[1], debit_line[5], amount, debit_line[1]))

                if credit_line[2]:
                    rows[1].append(credit_line)
                if debit_line[2]:
                    rows[0].append(debit_line)
        cr = self._cr

        cr.execute("SELECT mr.id, ml.id_90, ml.credit - ml.debit, u.id_90, mr.create_date, comp.id_90\n"
                   "FROM account_move_reconcile_61 mr\n"
                   "INNER JOIN account_move_line_61 AS ml ON ml.reconcile_id = mr.id OR ml.reconcile_partial_id = mr.id\n"
                   "LEFT JOIN res_company_61 AS comp ON comp.id = ml.company_id\n"
                   "LEFT JOIN res_users_61 AS u ON u.id = ml.create_uid\n"
                   "ORDER BY mr.id, debit+credit DESC")

        prev = False
        rows = [[],[]]
        for row in cr.fetchall():
            if row[0] != prev:
                create_reconcile(cr, rows)
                rows = [[],[]] #debit, credit
                prev = row[0]
            rows[row[2] > 0].append(list(row))
        create_reconcile(cr, rows)


        # Mise à jour des champs calculés liés aux rapprochements

        # /!\ WARNING : Requête de la MORT !!! Calcul de matched_percentage des pièces comptables
        cr.execute("UPDATE account_move AS m\n"
                   "SET matched_percentage = CASE WHEN lines.total_amount = 0 THEN 1 ELSE lines.total_reconciled / lines.total_amount END\n"
                   "FROM (SELECT recs.move_id, SUM(recs.amount) AS total_amount, SUM(recs.amount_reconciled) AS total_reconciled\n"
                   "      FROM account_move AS m\n"
                   "      LEFT JOIN (SELECT ml.move_id, ml.id, ml.user_type_id, ABS(ml.debit - ml.credit) AS amount, SUM(rec.amount) AS amount_reconciled\n"
                   "                 FROM account_move_line AS ml\n"
                   "                 LEFT JOIN account_partial_reconcile AS rec ON rec.credit_move_id = ml.id OR rec.debit_move_id = ml.id\n"
                   "                 GROUP BY ml.id\n"
                   "                ) AS recs ON recs.move_id = m.id\n"
                   "      LEFT JOIN account_account_type AS actype ON actype.id = recs.user_type_id\n"
                   "      WHERE actype.type IN ('receivable', 'payable')\n"
                   "      GROUP BY recs.move_id\n"
                   "     ) AS lines\n"
                   "WHERE lines.move_id = m.id")

        # Calcul de amount_residual et reconciled des écritures comptables
        cr.execute("UPDATE account_move_line AS l\n"
                   "SET amount_residual = l.debit - l.credit + rec.debit\n,"
                   "    reconciled = (l.debit + rec.debit = l.credit)\n"
                   "FROM (SELECT l.id, SUM(amount) AS debit\n"
                   "      FROM account_move_line AS l\n"
                   "      LEFT JOIN (\n" 
                   "       SELECT credit_move_id AS line_id, amount AS amount FROM account_partial_reconcile\n"
                   "       UNION\n"
                   "       SELECT debit_move_id, -amount FROM account_partial_reconcile) AS a ON a.line_id=l.id\n"
                   "      GROUP BY l.id) AS rec\n"
                   "WHERE rec.id = l.id")
   
        # Calcul des valeurs cash_basis des écritures comptables
        cr.execute("UPDATE account_move_line AS ml\n"
                   "SET debit_cash_basis = ml.debit * m.matched_percentage,\n"
                   "    credit_cash_basis = ml.credit * m.matched_percentage,\n"
                   "    balance_cash_basis = ml.balance * m.matched_percentage\n"
                   "FROM account_move AS m\n"
                   "INNER JOIN account_journal AS j ON j.id = m.journal_id\n"
                   "WHERE m.id = ml.move_id\n"
                   "  AND j.type IN ('sale', 'purchase')")

    @api.model
    def import_module_account(self):
        return (
            'account_account_type',
            'account_account',
            'account_analytic_account',
            'account_journal',
            'account_tax',
            'account_bank_statement',
            'account_bank_statement_line',
            'payment_mode',
            'account_move',
            'of_voucher_remise',
            'account_voucher',
            'account_payment_term',
            'account_payment_term_line',
            'account_fiscal_position',
            'account_fiscal_position_tax',
            'account_fiscal_position_account',
            'account_invoice',
            'account_invoice_line',
            'account_move_line', # Doit se placer après les factures pour le lien invoice_id
            'account_move_reconcile',
        )
