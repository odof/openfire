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
        if o._model._name == 'of.service':
            result['service'] = o
        return result

    @api.model
    def _get_dict_values(self, o, objects=None):
        if not objects:
            objects = self._get_objects(o)
        result = super(of_compose_mail,self)._get_dict_values(o, objects=objects)

        mois = jours = []
        date_fin = ''

        service = objects.get('service')
        if service:
            mois = [mois.name for mois in service.mois_ids]
            jours = [jour.name for jour in service.jour_ids]

            if service.date_fin:
                lang_code = self._context.get('lang', objects['partner'].lang)
                lang = self.env['res.lang'].search([('code','=', lang_code)])
    
                date_length = len((datetime.now()).strftime(DEFAULT_SERVER_DATE_FORMAT))
                # reformatage de la date (copie depuis report_sxw : rml_parse.formatLang())
                date_fin = datetime.strptime(service.date_fin[:date_length], DEFAULT_SERVER_DATE_FORMAT)
                date_fin = date_fin.strftime(lang.date_format.encode('utf-8'))

        result.update({
            's_name'    : service and service.name or '',
            's_mois'    : " ".join(mois),
            's_jour'    : " ".join(jours),
            's_note'    : service and service.note or '',
            's_template': service and service.template_id and service.template_id.name or '',
            's_echeance': date_fin,
        })
        return result
