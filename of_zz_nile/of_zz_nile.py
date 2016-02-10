# -*- coding: utf-8 -*-

from openerp import models, fields, api


# Catégories de activités feuilles de temps (module hr_timesheet)
class of_hr_timesheet_categ(models.Model):
    
    _name = "of.hr.timesheet.categ"
    
    name = fields.Char(u'Catégorie', size=32)
    parent_id = fields.Many2one('of.hr.timesheet.categ', 'Catégorie parente', select=True, ondelete='restrict')
    
    _constraints = [
        (models.Model._check_recursion, 'Error ! You can not create recursive category.', ['parent_id'])
    ]

    # Pour afficher la hiérarchie des catégories
    @api.multi
    def name_get(self):
        if not self._ids:
            return []
        res = []
        for record in self:
            name = [record.name]
            parent = record.parent_id
            while parent:
                name.append(parent.name)
                parent = parent.parent_id
            name = ' / '.join(name[::-1])
            res.append((record.id, name))
        return res


class account_analytic_line(models.Model):
    
    _inherit = 'account.analytic.line'
    
    of_categ_id = fields.Many2one('of.hr.timesheet.categ', u'Catégorie', required=True, ondelete='restrict')


class hr_timesheet_report(models.Model):
      
    _inherit = 'hr.timesheet.report'
      
    of_categ_id = fields.Many2one('of.hr.timesheet.categ', u'Catégorie', readonly=True)
    
    def _select(self):
        return super(hr_timesheet_report, self)._select() + ', aal.of_categ_id as of_categ_id\n'

    def _group_by(self):
        return super(hr_timesheet_report, self)._group_by() + ', aal.of_categ_id\n'
    
