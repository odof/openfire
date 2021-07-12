# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    @api.model_cr_context
    def _auto_init(self):
        # initialiser les champs d'autorisation d'accès par l'API, ne doit se déclencher qu'une fois
        cr = self._cr
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'crm_lead' AND column_name = 'of_api_create'")
        need_init = not bool(cr.fetchall())
        res = super(CRMLead, self)._auto_init()

        if need_init:
            cr.execute("UPDATE ir_model "
                       "SET of_api_auth = 't' "
                       "WHERE model = 'crm.lead'")
            cr.execute("UPDATE ir_model_fields "
                       "SET of_api_auth = 't' "
                       "WHERE model = 'crm.lead' "
                       "AND name IN ('description', 'of_infos_compl', 'name', 'planned_revenue', 'contact_name', "
                       "'is_company', 'function', 'street', 'street2', 'zip', 'city', 'phone', 'mobile', 'fax', "
                       "'email_from', 'referred')")
        return res

    of_api_create = fields.Boolean(string=u"Création par l'API OF", readonly=True)

    @api.model
    def create(self, vals):
        of_api_user = self.env.ref('of_web_api.of_api_user', raise_if_not_found=False)
        if of_api_user and self._uid == of_api_user.id:
            vals['of_api_create'] = True
        return super(CRMLead, self).create(vals)
