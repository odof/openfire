# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFResPartnerCheckDuplications(models.TransientModel):
    _name = 'of.res.partner.check.duplications'

    @api.model
    def default_get(self, fields_list):
        result = super(OFResPartnerCheckDuplications, self).default_get(fields_list)
        if 'duplication_ids' in result:
            info_txt = u""
            duplications = self.env['res.partner'].sudo().browse(result['duplication_ids'][0][2])
            for partner in duplications:
                forbidden_access = False
                try:
                    partner.sudo(self._uid).check_access_rights('read')
                    partner.sudo(self._uid).check_access_rule('read')
                except Exception:
                    forbidden_access = True
                if forbidden_access:
                    duplications -= partner
                    if not info_txt:
                        info_txt += \
                            "Potential duplicates exist but you do not have sufficient rights to view them." \
                            "Please contact your manager about this:\n"
                    info_txt += u"- %s\n" % partner.sudo().name
            result['duplication_ids'] = duplications.ids
            result['info_txt'] = info_txt
            result['display_list'] = bool(duplications)
        return result

    new_partner_id = fields.Many2one(comodel_name='res.partner', string="New partner")
    duplication_ids = fields.Many2many(comodel_name='res.partner', string="Potential duplicates")
    info_txt = fields.Text(string="Info text")
    display_list = fields.Boolean(string="Display list")

    def action_merge_partners(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.partner.merge.automatic.wizard',
            'context': {'active_ids': (self.duplication_ids + self.new_partner_id).ids},
            'target': 'new'
        }
