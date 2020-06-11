# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    of_dms_file_count = fields.Integer(string=u"Nombre de documents associés", compute='_compute_dms_file_count')

    @api.multi
    def _compute_dms_file_count(self):
        for partner in self:
            partner_dir = self.env['muk_dms.directory']\
                .search([('of_partner_id', '=', partner.commercial_partner_id.id)])
            if not partner_dir:
                self.of_dms_file_count = 0
            else:
                self.of_dms_file_count = self.env['muk_dms.file'].search([('directory', '=', partner_dir.id)],
                                                                         count=True)

    @api.multi
    def action_view_dms_files(self):
        self.ensure_one()
        if self.of_dms_file_count:
            partner_dir = self.env['muk_dms.directory']\
                .search([('of_partner_id', '=', self.commercial_partner_id.id)])
            action = self.env.ref('muk_dms.action_dms_file').read()[0]
            action['views'] = [(self.env.ref('muk_dms.view_dms_file_tree').id, 'tree'),
                               (self.env.ref('muk_dms.view_dms_file_kanban').id, 'kanban'),
                               (self.env.ref('muk_dms.view_dms_file_form').id, 'form')]
            action['domain'] = [('directory', '=', partner_dir.id)]
            return action

    @api.multi
    def write(self, vals):
        dir_obj = self.env['muk_dms.directory'].sudo()
        file_obj = self.env['muk_dms.file'].sudo()
        res = super(Partner, self).write(vals)
        if 'parent_id' in vals:
            for partner in self:
                partner_dir = dir_obj.of_get_partner_directory(partner)
                files = file_obj.search([('of_file_type', '=', 'related'),
                                         ('of_attachment_partner_id', 'child_of', partner.id)])
                partner_dir_old = files.mapped('directory')
                files.write({'directory': partner_dir.id})
                if partner_dir_old:
                    partner_dir_old.filtered(lambda d: not d.files).unlink()

        if 'name' in vals:
            partner_dir = dir_obj.search([('of_partner_id', 'in', self.ids)])

            # Le partenaire est renommé,
            if partner_dir:
                parent_dir = dir_obj.of_get_partner_parent_directory(self[0])
                partner_dir.write({'name': vals['name'],
                                   'parent_directory': parent_dir.id})
        return res
