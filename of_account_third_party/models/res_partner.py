# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import api, models
from odoo.tools.safe_eval import safe_eval

from odoo.addons.of_utils.models.misc import sanitize_text


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _ac_sanitize_name(self, name, max_length=12):
        """
        Helper method to sanitize the given name.
        Used through the safe_eval method for an automatic account code generation.
        """
        return sanitize_text(name)[max_length].upper()

    def _ac_filter_accounts(self, accounts, eval_str):
        """
        Helper method to filter the given list of accounts based on the provided string.
        Used through the safe_eval method for an automatic account code generation.
        """
        return [a for a in accounts if len(a.code) == len(eval_str) or a.code[len(eval_str) :].isdigit()]

    def _ac_sort_accounts(self, accounts):
        """
        Helper method to sort a list of accounts by their code in ascending order.
        Used through the safe_eval method for an automatic account code generation.
        """
        return sorted(accounts, key=lambda a: (len(a.code), a.code))

    def _ac_get_next_code(self, partner, eval_str):
        """
        Helper method to get the next code based on the given partner and string.
        Used through the safe_eval method for an automatic account code generation.
        """
        # search for accounts with the same prefix
        accounts = partner.env['account.account'].search([('code', '=like', f'{eval_str}%')])
        # filter and sort the accounts
        filtered_accounts = self._ac_filter_accounts(accounts, eval_str)
        sorted_accounts = self._ac_sort_accounts(filtered_accounts)
        # get the last code and increment it
        last_code = sorted_accounts[-1].code if sorted_accounts else '0' * (len(eval_str) + 1)
        return int(last_code[len(eval_str) :] or '1') + 1

    @api.model
    def _ac_get_code(self, company, prefix, digits, required=True, first_num=1, suffix=''):
        """
        Generate a unique code (with increment) based on the given parameters.

        Args:
            company (object): The company object.
            prefix (str): The prefix for the code.
            digits (int): The number of digits for the code.
            required (bool, optional): Whether the code is required. Defaults to True.
            first_num (int, optional): The starting number for the code. Defaults to 1.
            suffix (str, optional): The suffix for the code. Defaults to ''.

        Returns:
            str: The generated code.
        """

        def postgres_regexp_escape(text):
            return re.sub(r'([!$()*+.:<=>?[\]^{|}-])', r'\\\1', text)

        code_pattern = f'^{postgres_regexp_escape(prefix)}' + '\\d*' + postgres_regexp_escape(suffix) + '$'

        self.env.cr.execute(
            "SELECT code "
            "FROM account_account "
            "WHERE code ~ %s "
            "  AND company_id = %s "
            "ORDER BY char_length(code) DESC, code DESC "
            "LIMIT 1",
            (code_pattern, company.id),
        )
        prev_codes = self.env.cr.fetchone()
        prev_code = prev_codes and prev_codes[0]
        if not prev_code:
            if not required:
                return prefix + suffix
            prev_code = prefix + suffix
        num = first_num
        if prev_code != prefix + suffix:
            num = int(prev_code[len(prefix) : -len(suffix) or len(prev_code)]) + 1
        return f"{prefix}{num:0{digits}d}{suffix}"  # noqa : E231

    def _update_account(self, company, update_customer_account=False, update_supplier_account=False):
        """
        Update the third-party accounts for customers and suppliers.

        This method is responsible for creating or updating the third-party accounts
        for customers and suppliers based on the provided company.

        Args:
            company (object): The company for which the accounts need to be updated.
            If the company does not have a chart of accounts, its parent companies
            will be checked until a chart of accounts is found.
            update_customer_account (bool): If True, update the customer account.
            update_supplier_account (bool): If True, update the supplier account.
        """
        # Pas de création de compte de tiers pour les contacts, mais uniquement pour les vrais partenaires
        partners = self.mapped('commercial_partner_id')
        if not partners:
            return

        while not company.chart_template_id and company.parent_id:
            company = company.parent_id

        default_account_receivable = self.env['ir.property']._get('property_account_receivable_id', self._name)
        default_account_payable = self.env['ir.property']._get('property_account_payable_id', self._name)

        if not (default_account_payable and default_account_receivable):
            # La comptabilité de la société n'est pas configurée
            return

        for partner in partners:
            partner_values = {}
            if update_customer_account and company.of_customer_code:
                self._create_or_update_account(
                    partner,
                    default_account_receivable,
                    company,
                    partner_values,
                    'property_account_receivable_id',
                    'asset_receivable',
                    company.of_customer_code,
                )
            if update_supplier_account and company.of_supplier_code:
                self._create_or_update_account(
                    partner,
                    default_account_payable,
                    company,
                    partner_values,
                    'property_account_payable_id',
                    'liability_payable',
                    company.of_supplier_code,
                )
            if partner_values:
                partner.write(partner_values)

    def _create_or_update_account(
        self, partner, default_account, company, partner_values, field_name, account_type, code_expression
    ):
        if (getattr(partner, field_name) or default_account) == default_account:
            code, name = safe_eval(
                code_expression,
                {
                    'partner': partner,
                    'company': company,
                    'get_code': self._ac_get_code,
                    'sanitize_name': self._ac_sanitize_name,
                    'filter_accounts': self._ac_filter_accounts,
                    'sort_accounts': self._ac_sort_accounts,
                    'get_next_code': self._ac_get_next_code,
                    'sanitize': sanitize_text,
                },
            )
            ac_obj = self.env['account.account']
            if account := ac_obj.search([('code', '=', code), ('company_id', '=', company.id)], limit=1):
                partner_values[field_name] = account.id
                account.name = code
            else:
                partner_values[field_name] = ac_obj.create(
                    {
                        'account_type': account_type,
                        'code': code,
                        'name': name,
                        'reconcile': True,
                        'company_id': default_account.company_id.id,
                    }
                )

    def update_account(self, company=False, update_customer_account=False, update_supplier_account=False):
        """
        Creation/Update of third-party accounts for customers and suppliers.

        Args:
            company (object, optional) : The company for which the accounts need to be updated.
            If not specified, the creation of a third-party account is done according to the user's company.
        """
        company = company or self.env.user.company_id
        self._update_account(company, update_customer_account, update_supplier_account)
