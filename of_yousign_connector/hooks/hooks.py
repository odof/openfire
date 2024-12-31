# -*- coding: utf-8 -*-

import uuid

from odoo import api, models


class OFYousignConnectorHook(models.AbstractModel):
    _name = 'of.yousign.connector.hook'

    @api.model
    def _auto_init_res_company_hook_v16_0_1_0_0(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_yousign_connector')])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < "16.0.1.1.0"
        if actions_todo:
            cr = self._cr
            cr.execute(
                "SELECT 1 "
                "FROM information_schema.columns "
                "WHERE table_name = 'res_company' "
                "AND column_name = 'of_yousign_external_id'"
            )
            exists = bool(cr.fetchall())
            if not exists:
                cr.execute(
                    "ALTER TABLE res_company ADD COLUMN of_yousign_external_id character varying; "
                )
            dbname = cr.dbname

            cr.execute("SELECT id FROM res_company WHERE of_yousign_external_id IS NULL")
            for company_id, in cr.fetchall():
                external_id = '%s_%i_%s' % (dbname, company_id, uuid.uuid4())
                cr.execute(
                    "UPDATE res_company "
                    "SET of_yousign_external_id = %s "
                    "WHERE id = %s",
                    (external_id, company_id)
                )
