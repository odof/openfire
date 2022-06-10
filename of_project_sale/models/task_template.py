# -*- coding: utf8 -*-

from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

    of_planning_tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche du RDV")


class OFProjectTaskTemplate(models.Model):
    _name = 'of.project.task.template'
    _description = u"Modèle de tâches"

    name = fields.Char(string=u"Nom", required=True)
    duration = fields.Float(string=u"Durée", digits=(6, 2))
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string=u"Article", index=True)
    planning_tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche du RDV")
