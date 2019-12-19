# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    of_datastore_res_id = fields.Integer(string="ID on supplier database")

    @api.multi
    def arinna_synchronize(self):
        supplier = self.env['of.datastore.supplier'].sudo().search([('db_name', '=', 'arinna')])
        client = supplier.of_datastore_connect()
        ds_interv_obj = supplier.of_datastore_get_model(client, 'of.planning.intervention')
        for intervention in self:
            data = {
                'number': intervention.number,
                'name': intervention.name,
                'partner_id': intervention.partner_id.id,
                'address_id': intervention.address_id.id,
                'tache_id': intervention.tache_id.id,
                'employee_ids': [(6, False, intervention.employee_ids.ids)],
                'date': intervention.date,
                'duree': intervention.duree,
                'forcer_dates': True,
                'date_deadline_forcee': intervention.date_deadline,
                'description': intervention.description,
                'state': intervention.state,
            }
            if intervention.of_datastore_res_id:
                # Mise à jour des données
                supplier.of_datastore_write(ds_interv_obj, intervention.of_datastore_res_id, data)
            else:
                # Création d'intervention
                intervention.of_datastore_res_id = supplier.of_datastore_create(ds_interv_obj, data)
        return self.env['of.popup.wizard'].popup_return(
            u"Les interventions sélectionnées ont bien été mises à jour chez Arinna."
        )
