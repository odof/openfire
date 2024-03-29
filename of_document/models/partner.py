# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
                partner.of_dms_file_count = 0
            else:
                partner.of_dms_file_count = self.env['muk_dms.file'].search([
                    ('directory', 'child_of', partner_dir.id)], count=True)

    @api.multi
    def action_view_dms_files(self):
        self.ensure_one()
        if self.of_dms_file_count:
            return {
                'type': 'ir.actions.client',
                'name': 'DocumentTreeView',
                'tag': 'muk_dms_views.documents',
                'context': {
                    'partner_id': self.id,
                    'partner_name': self.display_name,
                    'parent_directory_id': self.env['muk_dms.directory'].of_get_partner_directory(self).id,
                },
            }

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
