# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFResPartnerCheckDuplications(models.TransientModel):
    _name = "of.res.partner.check.duplications"

    @api.model
    def default_get(self, fields):
        result = super(OFResPartnerCheckDuplications, self).default_get(fields)
        if 'duplication_ids' in result:
            info_txt = u""
            duplications = self.env['res.partner'].sudo().browse(result['duplication_ids'][0][2])
            for partner in duplications:
                forbidden_access = False
                try:
                    partner.sudo(self._uid).check_access_rights('read')
                    partner.sudo(self._uid).check_access_rule('read')
                except:
                    forbidden_access = True
                if forbidden_access:
                    duplications -= partner
                    if not info_txt:
                        info_txt += u"Des doublons potentiels existent mais vous n'avez pas les droits suffisants " \
                                    u"pour les consulter. Merci de contacter votre responsable sur ce sujet :\n"
                    info_txt += u"- %s\n" % partner.sudo().name
            result['duplication_ids'] = duplications.ids
            result['info_txt'] = info_txt
            if duplications:
                result['display_list'] = True
            else:
                result['display_list'] = False
        return result

    duplication_ids = fields.Many2many(comodel_name='res.partner', string=u"Doublons potentiels")
    info_txt = fields.Text()
    display_list = fields.Boolean()
