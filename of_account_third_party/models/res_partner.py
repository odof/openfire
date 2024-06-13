# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import api, models
from odoo.tools.safe_eval import safe_eval

from odoo.addons.of_utils.models.misc import sanitize_text


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def get_code(self, company, prefix, digits, required=True, first_num=1, suffix=''):
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
        return f"{prefix}{num: 0{digits}d}{suffix}"

    def _update_account(self, company):
        """
        Update the third-party accounts for customers and suppliers.

        This method is responsible for creating or updating the third-party accounts
        for customers and suppliers based on the provided company.

        Args:
            company (object): The company for which the accounts need to be updated.
            If the company does not have a chart of accounts, its parent companies
            will be checked until a chart of accounts is found.
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
            data = {}
            if partner.is_customer and company.of_customer_code:
                self._create_or_update_account(
                    partner,
                    default_account_receivable,
                    company,
                    data,
                    'property_account_receivable_id',
                    'asset_receivable',
                    company.of_customer_code,
                )

            if partner.is_supplier and company.of_supplier_code:
                self._create_or_update_account(
                    partner,
                    default_account_payable,
                    company,
                    data,
                    'property_account_payable_id',
                    'liability_payable',
                    company.of_supplier_code,
                )
            if data:
                partner.write(data)

    def _create_or_update_account(
        self, partner, default_account, company, data, field_name, account_type, code_expression
    ):
        if (getattr(partner, field_name) or default_account) == default_account:
            code, name = safe_eval(
                code_expression,
                {
                    'partner': partner,
                    'company': company,
                    'get_code': lambda prefix, digits, required=True, first_num=1, suffix='': self.get_code(
                        company, prefix, digits, required, first_num, suffix
                    ),
                    'sanitize': sanitize_text,
                },
            )
            ac_obj = self.env['account.account']
            if account := ac_obj.search([('code', '=', code), ('company_id', '=', company.id)], limit=1):
                data[field_name] = account.id
                account.name = code
            else:
                account_data = {
                    'account_type': account_type,
                    'code': code,
                    'name': name,
                    'reconcile': True,
                    'company_id': default_account.company_id.id,
                }
                data[field_name] = ac_obj.create(account_data)

    def update_account(self, company=False):
        """
        Creation/Update of third-party accounts for customers and suppliers.

        Args:
            company (object, optional) : The company for which the accounts need to be updated.
            If not specified, the creation of a third-party account is done according to the user's company.
        """
        company = company or self.env.user.company_id
        self._update_account(company)
