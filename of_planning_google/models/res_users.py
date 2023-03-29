# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_google_company_id = fields.Many2one(
        string=u"Google calendar company", comodel_name='res.company', default=lambda u: u.company_id.id)
    of_google_calendar_last_sync_date = fields.Datetime(
        string=u"Last synchro date", copy=False, hel=u"For field operations planning")


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    email_synchro = fields.Char(string=u"Synchronized email", compute='_compute_email_synchro', store=True)

    @api.depends('work_email', 'user_id.partner_id.email')
    def _compute_email_synchro(self):
        for emp in self:
            if emp.user_id:
                emp.email_synchro = emp.user_id.partner_id.email
            else:
                emp.email_synchro = emp.work_email

    @api.multi
    def peut_faire(self, tache, all_required=False):
        google_task = self.env.ref('of_planning_google.tache_google', raise_if_not_found=False)
        if google_task and google_task.id == tache.id:
            return True
        return super(HrEmployee, self).peut_faire(tache, all_required)
