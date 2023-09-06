# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def write(self, vals):
        company_obj = self.env['res.company']
        activity_obj = self.env['of.crm.activity'].sudo()
        if 'company_ids' in vals:
            for user in self:
                old_companies = user.company_ids
                new_companies = company_obj.browse(vals['company_ids'] and vals['company_ids'][0][2] or [])
                deleted_companies = old_companies - new_companies
                # Si une société est retiré d'un utilisateur, on vide les champs auteur et vendeur des activités
                # de cet utilisateur liées au devis de cette société
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
        return super(ResUsers, self).write(vals)
