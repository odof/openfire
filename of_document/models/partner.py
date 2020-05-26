# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    of_dms_file_count = fields.Integer(string=u"Nombre de documents associés", compute='_compute_dms_file_count')

    @api.multi
    def _compute_dms_file_count(self):
        for partner in self:
            # Search top partner directory
            top_partner = partner
            while top_partner.parent_id:
                top_partner = top_partner.parent_id
            partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
            if not partner_dir:
                self.of_dms_file_count = 0
            else:
                self.of_dms_file_count = len(self.env['muk_dms.file'].search([('directory', '=', partner_dir.id)]))

    @api.multi
    def action_view_dms_files(self):
        self.ensure_one()
        if self.of_dms_file_count:
            # Search top partner directory
            top_partner = self
            while top_partner.parent_id:
                top_partner = top_partner.parent_id
            partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
            action = self.env.ref('muk_dms.action_dms_file').read()[0]
            action['views'] = [(self.env.ref('muk_dms.view_dms_file_tree').id, 'tree'),
                               (self.env.ref('muk_dms.view_dms_file_kanban').id, 'kanban'),
                               (self.env.ref('muk_dms.view_dms_file_form').id, 'form')]
            action['domain'] = [('directory', '=', partner_dir.id)]
            return action
