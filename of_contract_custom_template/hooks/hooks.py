# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFContractCustomTemplateHooks(models.AbstractModel):
    _name = 'of.contract.custom.template.hooks'

    @api.model
    def _post_hook_install(self):
        """
        On install, init default values for each company for the following fields
        of.contract.template.property_journal_id
        """
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_contract_custom_template')])
        actions_todo = module_self and not module_self.latest_version
        if actions_todo:
            journal_obj = self.env['account.journal']
            companies = self.env['res.company'].search([])
            cr = self.env.cr
            property_journal_id_infos = {
                'model': 'of.contract.template',
                'field': 'property_journal_id',
            }
            cr.execute(
                "SELECT id FROM ir_model_fields WHERE model=%(model)s AND name=%(field)s", property_journal_id_infos)
            property_journal_id_infos['fields_id'] = cr.fetchone()
            for company in companies:
                invoicing_company = getattr(company, 'accounting_company_id', company)
                if invoicing_company != company:
                    continue
                domain = [('type', '=', 'sale'), ('company_id', '=', invoicing_company.id)]
                journal = journal_obj.search(domain, limit=1)
                if not journal:
                    continue
                current = property_journal_id_infos.copy()
                current.update({
                    'target': '%s,%s' % (journal._name, journal.id),
                    'company_id': company.id,
                })
                cr.execute(
                    """
                    INSERT INTO ir_property(name, type, fields_id, company_id, value_reference, create_date, create_uid)
                    VALUES (%(field)s, 'many2one', %(fields_id)s, %(company_id)s, %(target)s, now(), 1)
                    """,
                    current
                )
