# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    company_id = fields.Many2one(default=False)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        super(ProjectIssue, self)._onchange_partner_id()
        if self.partner_id:
            self.company_id = self.partner_id.company_id
