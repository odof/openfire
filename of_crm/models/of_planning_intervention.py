# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    opportunity_id = fields.Many2one(
        comodel_name='crm.lead', string=u"Opportunité associée",
        domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")

    @api.model
    def create(self, vals):
        res = super(OfPlanningIntervention, self).create(vals)

        # CRM stages
        if res.opportunity_id:
            stages = self.env['crm.stage'].search(
                [('of_auto_model_name', '=', 'of.planning.intervention'),
                 ('sequence', '>', res.opportunity_id.stage_id.sequence)], order='sequence desc')
            for stage in stages:
                if stage.of_auto_field_id.name in vals:
                    value = vals.get(stage.of_auto_field_id.name)
                    ctx = {'value': value,
                           'fields': fields,
                           'self': self.sudo()}
                    code_res = safe_eval("value %s" % stage.of_auto_comparison_code, ctx)
                    if code_res:
                        res.opportunity_id.write({'stage_id': stage.id})
                        break

        return res

    @api.multi
    def _write(self, values):
        res = super(OfPlanningIntervention, self)._write(values)

        # CRM stages
        for rec in self:
            if rec.opportunity_id:
                stages = self.env['crm.stage'].search(
                    [('of_auto_model_name', '=', 'of.planning.intervention'),
                     ('sequence', '>', rec.opportunity_id.stage_id.sequence)], order='sequence desc')
                for stage in stages:
                    if stage.of_auto_field_id.name in values:
                        value = values.get(stage.of_auto_field_id.name)
                        ctx = {'value': value,
                               'fields': fields,
                               'self': self.sudo()}
                        code_res = safe_eval("value %s" % stage.of_auto_comparison_code, ctx)
                        if code_res:
                            rec.opportunity_id.write({'stage_id': stage.id})
                            break

        return res
