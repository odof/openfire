# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    @api.model_cr_context
    def _auto_init(self):
        # initialiser les champs d'autorisation d'accès par l'API, ne doit se déclencher qu'une fois
        cr = self._cr
        cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'of_planning_intervention' AND column_name = 'api_create'")
        need_init = not bool(cr.fetchall())
        res = super(OFPlanningIntervention, self)._auto_init()

        if need_init:
            cr.execute(
                "UPDATE ir_model "
                "SET of_api_auth = 't' "
                "WHERE model = 'of.planning.intervention'")
            cr.execute(
                "UPDATE ir_model_fields "
                "SET of_api_auth = 't' "
                "WHERE model = 'of.planning.intervention' "
                "AND name IN ('service_id', 'date', 'employee_ids', 'employee_main_id', 'external_id', "
                "'state', 'company_id')")
        return res

    api_create = fields.Boolean(string=u"Création par l'API OF", readonly=True)
    external_id = fields.Char(string=u"Identifiant externe", readonly=True)

    _sql_constraints = [
        ('external_id_uniq', 'unique(external_id)', u"L'identifiant externe doit être unique"),
    ]

    @api.model
    def create(self, vals):
        of_api_user = self.env.ref('of_web_api.of_api_user', raise_if_not_found=False)
        if of_api_user and self._uid == of_api_user.id:
            vals['api_create'] = True
        return super(OFPlanningIntervention, self).create(vals)
