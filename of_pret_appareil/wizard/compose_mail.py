# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _

class of_compose_mail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o, data):
        result = super(of_compose_mail,self)._get_objects(o, data)
        # Triche : utilisation d'un appareil prêté comme un parc installé, en raison de la similarité des champs
        if o._model._name == 'of.pret.appareil':
            result['parc_installe'] = o
            result['sav'] = o.of_pret_appareil_line_ids and o.of_pret_appareil_line_ids[0].sav_id
        return result
