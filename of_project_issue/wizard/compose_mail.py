# -*- coding: utf-8 -*-

from openerp import models, api

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime

# Pour la génération de pdf depuis le SAV
class of_compose_mail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o):
        result = super(of_compose_mail,self)._get_objects(o)
        if o._model._name == 'project.issue':
            result['sav'] = o
        return result

    @api.model
    def _get_dict_values(self, o, objects=None):
        if not objects:
            objects = self._get_objects(o)
        result = super(of_compose_mail,self)._get_dict_values(o, objects=objects)

        sav = objects.get('sav')
        sav_categ = sav and sav.of_categorie_id
        sav_categ_mere = sav_categ and sav_categ.parent_id
        while sav_categ_mere.parent_id:
            sav_categ_mere = sav_categ_mere.parent_id

        result.update({
            'sav_of_code'      : sav and sav.of_code,
            'sav_name'         : sav and sav.name or '',
            'sav_user'         : sav and sav.user_id and sav.user_id.name or '',
            'sav_description'  : sav and sav.description or '',
            'sav_pieces'       : sav and sav.of_piece_commande or '',
            'sav_intervention' : sav and sav.of_intervention or '',
            'sav_categ'        : sav_categ and sav_categ.name or '',
            'sav_categ_mere'   : sav_categ_mere and sav_categ_mere.name or '',
            'sav_categ_complet': sav_categ and sav_categ.name_get()[0][1] or '',

            # Lignes gardées pour compatibilité, mais pi référence désormais les parcs installés
            'pi_of_code'              : sav and sav.of_code,
            'pi_name'                 : sav and sav.name or '',
            'pi_description'          : sav and sav.description or '',
        })

        sav_date = sav and sav.date or ''
        if sav_date:
            lang_obj = self.env['res.lang']

            partner = objects.get('partner',False)
            lang_code = self._context.get('lang', partner.lang)
            lang = lang_obj.search([('code','=', lang_code)])

            date_length = len((datetime.now()).strftime(DEFAULT_SERVER_DATE_FORMAT))
            sav_date = datetime.strptime(sav_date[:date_length], DEFAULT_SERVER_DATE_FORMAT)
            sav_date = sav_date.strftime(lang.date_format.encode('utf-8'))
            result['sav_date'] = sav_date
        return result
