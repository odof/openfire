# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class OfCrmStageAutoUpdate(models.AbstractModel):
    """
    Modèle à hériter pour bénéficier des fonctions de mise à jour auto d'étape CRM.
    """
    _name = 'of.crm.stage.auto.update'

    opportunity_id = fields.Many2one(
            comodel_name='crm.lead', string=u"Opportunité associée")

    @api.model
    def create(self, vals):
        res = super(OfCrmStageAutoUpdate, self).create(vals)

        # CRM stages
        if res.opportunity_id:
            stages = self.env['crm.stage'].search(
                    [('of_auto_model_name', '=', self._name),
                     ('sequence', '>', res.opportunity_id.stage_id.sequence)], order='sequence desc')
            for stage in stages:
                if stage.of_auto_field_id.name in vals:
                    value = vals.get(stage.of_auto_field_id.name)
                    ctx = {'value': value,
                           'fields': fields,
                           'self': self.sudo()}
                    code_res = safe_eval("value %s" % (stage.of_auto_comparison_code or ''), ctx)
                    if code_res:
                        res.with_context(crm_stage_auto_update=True).opportunity_id.write({'stage_id': stage.id})
                        break

        return res

    @api.multi
    def _write(self, values):
        res = super(OfCrmStageAutoUpdate, self)._write(values)

        # CRM stages
        for rec in self.sudo():
            if rec.opportunity_id:
                stages = self.env['crm.stage'].search(
                        [('of_auto_model_name', '=', self._name),
                         ('sequence', '>', rec.opportunity_id.stage_id.sequence)], order='sequence desc')
                for stage in stages:
                    if stage.of_auto_field_id.name in values or 'opportunity_id' in values:
                        value = rec[stage.of_auto_field_id.name]
                        if hasattr(value, 'id'):
                            value = value['id']
                        ctx = {'value': value,
                               'fields': fields,
                               'self': self.sudo()}
                        code_res = safe_eval("value %s" % (stage.of_auto_comparison_code or ''), ctx)
                        if code_res:
                            rec.with_context(crm_stage_auto_update=True).opportunity_id.write({'stage_id': stage.id})
                            break

        return res
