# -*- coding: utf-8 -*-

from odoo import models, fields, api

# Catégories activités feuilles de temps (module hr_timesheet)
class OFHrTimesheetCateg(models.Model):
    _name = "of.hr.timesheet.categ"

    name = fields.Char(u'Catégorie', size=32)
    parent_id = fields.Many2one('of.hr.timesheet.categ', 'Catégorie parente', index=True, ondelete='restrict')

    _constraints = [
        (models.Model._check_recursion, u'Erreur ! Vous ne pouvez pas créer de catégorie récursive.', ['parent_id'])
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

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    of_categ_id = fields.Many2one('of.hr.timesheet.categ', u'Catégorie', ondelete='restrict')

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    of_categ_id = fields.Many2one('of.hr.timesheet.categ', u'Catégorie', ondelete='restrict')

class ProjectTask(models.Model):
    _inherit = 'project.task'

    of_categ_id = fields.Many2one('of.hr.timesheet.categ', u'Catégorie', readonly=True)

class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    of_categ_id = fields.Many2one('of.hr.timesheet.categ', u'Catégorie', readonly=True)

    def _select(self):
        return super(ReportProjectTaskUser, self)._select() + ', t.of_categ_id as of_categ_id\n'
  
    def _group_by(self):
        return super(ReportProjectTaskUser, self)._group_by() + ', t.of_categ_id\n'
