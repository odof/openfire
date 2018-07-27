# -*- coding: utf-8 -*-

from odoo import models, api
import time

class of_gesdoc_import(models.TransientModel):
    _inherit = 'of.gesdoc.import'

    @api.model
    def import_data_obj(self, data, obj):
        if obj._name == 'project.issue':
            result = {field[3:]: data[field] for field in ('pi_name', 'pi_description') if field in data}

            # Champs many2one
            if 'user' in data:
                if not obj.user_id or obj.user_id.name != data['user']:
                    user = self.env['res.users'].search([('name', 'ilike', data['user'])])
                    if user:
                        result['user_id'] = user.id
        else:
            result = super(of_gesdoc_import, self).import_data_obj(data, obj)
        return result

    @api.multi
    def import_data(self, data):
        result = super(of_gesdoc_import, self).import_data(data)
        if 'pi_of_code' in data:
            # Detection de la clef
            issue = self.env['project.issue'].search([('of_code', '=', data['pi_of_code'])])
            if issue:
                vals = self.import_data_obj(data, issue)
                if vals:
                    issue.write(vals)
                    date = time.strftime('%d/%m/%Y')
                    self.env['ir.attachment'].create({
                        'name': 'Import "%s" du %s' % (self.template_id.name, date),
                        'datas_fname': self.file_name,
                        'res_model': 'project.issue',
                        'res_id': issue.id,
                        'type': 'binary',
                        'datas': self.file,
                    })
                if not result and issue.partner_id:
                    # @todo: Mettre a jour les donnees du partenaire (adresses)
                    pass

                view = self.env.ref('project_issue.project_issue_form_view')
                return {
                    'name': 'Issues',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view.id,
                    'res_model': 'project.issue',
                    'type': 'ir.actions.act_window',
                    'res_id': issue.id,
                    'context': self._context,
                }
        return result
