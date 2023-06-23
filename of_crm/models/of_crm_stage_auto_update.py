# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class OfCrmStageAutoUpdate(models.AbstractModel):
    """Model to be inherited to benefit from CRM step's auto-update functions"""

    _name = 'of.crm.stage.auto.update'
    _description = __doc__

    opportunity_id = fields.Many2one(comodel_name='crm.lead', string="Related opportunity")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        # CRM stages
        if records.opportunity_id:
            stages = self.env['crm.stage'].search(
                [
                    ('of_auto_model_name', '=', self._name),
                    ('sequence', '>', min(records.opportunity_id.stage_id.mapped('sequence'))),
                ],
                order='sequence desc',
            )

            for vals, record in zip(vals_list, records):
                if not record.opportunity_id:
                    continue
                for stage in stages:
                    if stage.sequence <= record.opportunity_id.stage_id.sequence:
                        continue
                    if stage.of_auto_field_id.name in vals:
                        value = vals.get(stage.of_auto_field_id.name)
                        ctx = {'value': value, 'fields': fields, 'self': self.sudo()}
                        if safe_eval(f"value {stage.of_auto_comparison_code or ''}", ctx):
                            record.with_context(crm_stage_auto_update=True).opportunity_id.write({'stage_id': stage.id})
                            break
        return records

    def write(self, values):
        res = super().write(values)

        # CRM stages
        for record in self.sudo():
            if record.opportunity_id:
                stages = self.env['crm.stage'].search(
                    [
                        ('of_auto_model_name', '=', self._name),
                        ('sequence', '>', record.opportunity_id.stage_id.sequence),
                    ],
                    order='sequence desc',
                )
                for stage in stages:
                    if stage.of_auto_field_id.name in values or 'opportunity_id' in values:
                        value = record[stage.of_auto_field_id.name]
                        if hasattr(value, 'id'):
                            value = value['id']
                        ctx = {'value': value, 'fields': fields, 'self': self.sudo()}
                        if safe_eval(f"value {stage.of_auto_comparison_code or ''}", ctx):
                            record.with_context(crm_stage_auto_update=True).opportunity_id.write({'stage_id': stage.id})
                            break
        return res
