# -*- coding: utf-8 -*-

from odoo import models, api

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


# Pour la génération de pdf depuis le SAV
class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o):
        result = super(OfComposeMail, self)._get_objects(o)
        result['sav'] = o.name == 'project.issue' and o or self.env['project.issue']
        return result

    @api.model
    def _get_dict_values(self, o, objects):
        result = super(OfComposeMail, self)._get_dict_values(o, objects)

        sav = objects['sav']
        sav_categ = sav.of_categorie_id
        sav_categ_mere = sav_categ.parent_id
        if sav_categ_mere:
            while sav_categ_mere.parent_id:
                sav_categ_mere = sav_categ_mere.parent_id

        result.update({
            'sav_of_code'      : sav.of_code,
            'sav_date'         : sav.date and sav.date[:10] or '',
            'sav_name'         : sav.name or '',
            'sav_user'         : sav.user_id.name or '',
            'sav_description'  : sav.description or '',
            'sav_pieces'       : sav.of_piece_commande or '',
            'sav_intervention' : sav.of_intervention or '',
            'sav_categ'        : sav_categ.name or '',
            'sav_categ_mere'   : sav_categ_mere.name or '',
            'sav_categ_complet': sav_categ and sav_categ.name_get()[0][1] or '',

            # Lignes gardées pour compatibilité, mais pi référence désormais les parcs installés
            'pi_of_code'              : sav.of_code,
            'pi_name'                 : sav.name or '',
            'pi_description'          : sav.description or '',
        })

        sav_date = sav.date or ''
        if sav_date:
            lang_obj = self.env['res.lang']

            partner = objects.get('partner', False)
            lang_code = self._context.get('lang', partner.lang)
            lang = lang_obj.search([('code', '=', lang_code)])

            date_length = len((datetime.now()).strftime(DEFAULT_SERVER_DATE_FORMAT))
            sav_date = datetime.strptime(sav_date[:date_length], DEFAULT_SERVER_DATE_FORMAT)
            sav_date = sav_date.strftime(lang.date_format.encode('utf-8'))
            result['sav_date'] = sav_date
        return result
