# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, models, fields
from odoo.addons.calendar.models.calendar import get_real_ids


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    group_of_group_planning_intervention_recurring = fields.Boolean(
        string=u"Gérer les RDVs réguliers",
        implied_group='of_planning_recurring.of_group_planning_intervention_recurring')

    @api.onchange('group_of_group_planning_intervention_recurring')
    def _onchange_group_of_group_planning_intervention_recurring(self):
        type_misc = self.env.ref('of_planning_recurring.of_service_type_misc')
        if type_misc and self.group_of_group_planning_intervention_recurring:
            type_misc.write({'active': True})
        elif type_misc:
            type_misc.write({'active': False})


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        """ Convert the search on real ids in the case it was asked on virtual ids, then call super() """
        args = list(args)
        if any([leaf for leaf in args if leaf[0] == "res_model" and leaf[2] == 'of.planning.intervention']):
            for index in range(len(args)):
                if args[index][0] == "res_id" and isinstance(args[index][2], basestring):
                    args[index] = (args[index][0], args[index][1], get_real_ids(args[index][2]))
        return super(Attachment, self).search(args, offset=offset, limit=limit, order=order, count=count)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def _find_allowed_model_wise(self, doc_model, doc_dict):
        if doc_model == 'of.planning.intervention':
            order = self._context.get('order', self.env[doc_model]._order)
            for virtual_id in self.env[doc_model].browse(doc_dict.keys()).get_recurrent_ids([], order=order):
                doc_dict.setdefault(virtual_id, doc_dict[get_real_ids(virtual_id)])
        return super(MailMessage, self)._find_allowed_model_wise(doc_model, doc_dict)


class OFJours(models.Model):
    _inherit = 'of.jours'

    @api.multi
    def get_rec_fields(self):
        corres_dict = {
            'lun.': 'mo',
            'mar.': 'tu',
            'mer.': 'we',
            'jeu.': 'th',
            'ven.': 'fr',
            'sam.': 'sa',
            'dim.': 'su',
        }
        abr_list = self.mapped('abr')
        return {corres_dict[abr]: bool(abr in abr_list) for abr in corres_dict.keys()}
