# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class OFHoraireSaveProfil(models.Model):
    _name = 'of.horaire.save.profil'

    name = fields.Char(string=u"Libellé", required=True)

    @api.multi
    def action_confirm(self):
        model = self._context['active_model']
        obj = self.env[model].browse(self._context['active_id'])

        if model == 'of.horaires.segment':
            creneaux = obj.creneau_ids
        # elif model == 'hr.employee':
        #     creneaux = obj.of_creneau_ids
        else:
            raise UserError(_("Échec de la sauvegarde : horaires non trouvés."))
        self.env['of.horaires.profil'].create({
            'name': self.name,
            'creneau_ids': creneaux,
        })
        return True
