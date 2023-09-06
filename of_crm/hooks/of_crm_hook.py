# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class OFCrmHook(models.AbstractModel):
    _name = 'of.crm.hook'

    def _empty_activity_author(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_crm'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.1.4' or False
        if actions_todo:
            user_obj = self.env['res.users']
            company_obj = self.env['res.company']
            activity_obj = self.env['of.crm.activity']

            users = user_obj.search([])
            companies = company_obj.search([])

            for user in users:
                deleted_companies = companies - user.company_ids
                # On vide les champs auteur et vendeur des activités des utilisateurs
                # dont les devis sont sur une société auquel ces utilisateurs ne sont pas liés
                if deleted_companies:
                    activities = activity_obj.with_context(active_test=False).search([
                        ('origin', '=', 'sale_order'),
                        ('user_id', '=', user.id),
                        ('order_id.company_id', 'in', deleted_companies.ids)
                    ])
                    activities.write({
                        'user_id': False,
                        'vendor_id': False,
                    })
