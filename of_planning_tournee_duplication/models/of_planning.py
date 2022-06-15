# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    already_duplicated = fields.Boolean(
        string=u"Déjà dupliqué", copy=False,
        help=u"Si coché ce RDV a provoqué la création d'un nouveau RDV via le menu 'Duplication RDV'"
    )
    is_duplication = fields.Boolean(
        string=u"RDV dupliqué", copy=False,
        help=u"Si coché ce RDV a été créé via le menu 'Duplication RDV'"
    )


class OfPlanningTag(models.Model):
    _inherit = 'of.planning.tag'

    @api.multi
    def unlink(self):
        for record in (self.env.ref('of_planning_tournee_duplication.of_planning_tournee_planning_tag_duplique',
                                    raise_if_not_found=False),
                       self.env.ref(
                           'of_planning_tournee_duplication.of_planning_tournee_planning_tag_cree_par_duplication',
                           raise_if_not_found=False),
                       self.env.ref(
                           'of_planning_tournee_duplication.of_planning_tournee_planning_tag_alerte_duplication',
                           raise_if_not_found=False)
                       ):
            if record and record in self:
                raise UserError(u"Impossible de supprimer l'étiquette %s" % record.name)
        res = super(OfPlanningTag, self).unlink()
        return res
