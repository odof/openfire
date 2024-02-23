# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.http import request
from odoo.addons.of_web_api.controllers.main import OFAPIWeb
from dateutil.relativedelta import relativedelta
import pytz


class OFAPIWebPlanning(OFAPIWeb):

    def create_record(self, model_name, vals):
        u"""Héritage pour éviter la duplication de RDV"""
        planning_obj = request.env['of.planning.intervention']
        if model_name == 'of.planning.intervention':
            rdv = False
            # si le contenu de vals['employee_ids'] n'est pas un Iterable, on a probablement reçu une list d'int
            # il faut transformer la valeur pour que ce soit intégré
            ids_list = []
            # Conversion des datetime en GMT
            user_tz = pytz.timezone(request._context.get('tz') or request.env.user.tz)
            for field_name in vals:
                if field_name in planning_obj._fields and planning_obj._fields[field_name].type == 'datetime':
                    dt = fields.Datetime.from_string(vals[field_name])
                    dt = user_tz.localize(dt).astimezone(pytz.utc)
                    vals[field_name] = fields.Datetime.to_string(dt)

            if vals.get('employee_ids') and (isinstance(vals['employee_ids'], (list, tuple))) \
                    and (not isinstance(vals['employee_ids'][0], (list, tuple))):
                for id in vals['employee_ids']:
                    if isinstance(id, int) and id not in ids_list:
                        ids_list.append(id)
                vals['employee_ids'] = [(6, 0, ids_list)]
            if vals.get('external_id'):
                rdv = planning_obj.search([('external_id', '=', vals['external_id'])])
            if rdv:
                # on a trouvé un RDV, on met à jour au lieu de créer
                # retirer de vals les données qui ne seront pas mises à jour
                vals.pop('company_id', False)
                vals.pop('service_id', False)
                vals.pop('external_id')
                if vals.get('date') and vals['date'] == rdv.date:
                    vals.pop('date')
                elif vals.get('date') and rdv.forcer_dates:
                    # il faut changer la date de fin forcée
                    date = fields.Datetime.from_string(vals['date'])
                    date += relativedelta(hours=rdv.duree)
                    vals['date_deadline_forcee'] = fields.Datetime.to_string(date)
                if ids_list and set(ids_list) == set(rdv.employee_ids.ids):
                    vals.pop('employee_ids')
                if vals.get('employe_main_id') and vals['employe_main_id'] == rdv.employe_main_id.id:
                    vals.pop('employe_main_id')
                if vals.get('state') and vals['state'] == rdv.state:
                    vals.pop('state')
                elif vals.get('state') == 'cancel':
                    pickings = rdv.picking_ids.filtered(lambda p: p.state not in ('cancel', 'done'))
                    purchase_orders = pickings.of_purchase_ids.filtered(
                        lambda p: p.state in ('draft', 'sent', 'to_approve'))
                    if pickings:
                        pickings.action_cancel()
                    if purchase_orders:
                        purchase_orders.button_cancel()
                if vals:
                    rdv.write(vals)
                # on vérifie que l'employé principal est toujours dans la liste des employés du rdv
                # si ce n'est pas le cas, il faut le recalculer
                if rdv.employee_main_id.id not in rdv.employee_ids.ids:
                    rdv._onchange_employee_main_id()
                return rdv
            else:  # création d'un nouveau RDV
                new_rdv = planning_obj.new(vals)
                # récupère la majorité des informations via ce onchange
                new_rdv._onchange_service_id()
                # exécution des onchanges pour récupérer d'autres informations
                new_rdv._onchange_address_id()
                new_rdv._onchange_partner_id()
                if not rdv.employee_main_id:
                    new_rdv._onchange_employee_main_id()
                new_rdv.onchange_template_id()
                # réappliquer le onchange pour assurer que les infos de la DI n'ont pas été écrasées
                new_rdv._onchange_service_id()
                new_rdv.update({
                    'company_id': vals.get('company_id', new_rdv.company_id),
                    'forcer_dates': True,
                    'verif_dispo': False,
                    'duree': new_rdv.service_id.duree or new_rdv.tache_id.duree,
                })
                new_rdv.onchange_company_id()
                new_rdv._onchange_forcer_dates()
                vals = planning_obj._convert_to_write(new_rdv._cache)
        return super(OFAPIWebPlanning, self).create_record(model_name, vals)
