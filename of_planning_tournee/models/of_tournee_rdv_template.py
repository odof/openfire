# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.addons.of_planning_tournee.models.of_intervention_settings import SELECTION_SEARCH_TYPES
from odoo.addons.of_planning_tournee.models.of_intervention_settings import SELECTION_SEARCH_MODES


class OFTourneeRdvTemplate(models.Model):
    _name = 'of.tournee.rdv.template'

    name = fields.Char(string=u"Nom", required=True)
    employee_ids = fields.Many2many(comodel_name='hr.employee', string=u"Intervenant(s)")
    task_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche")
    template_id = fields.Many2one(comodel_name='of.planning.intervention.template', string=u"Modèle d'intervention")
    search_type = fields.Selection(selection=SELECTION_SEARCH_TYPES, string=u"Type de recherche")
    search_mode = fields.Selection(selection=SELECTION_SEARCH_MODES, string=u"Mode de recherche")

    access_user_ids = fields.Many2many(
        comodel_name='res.users', relation='of_tournee_rdv_template_access_users_rel', column1='template_id',
        column2='user_id', string=u"Accessible par")
    default_user_ids = fields.Many2many(
        comodel_name='res.users', relation='of_tournee_rdv_template_default_users_rel', column1='template_id',
        column2='user_id', string=u"Par défaut pour")
