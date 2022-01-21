# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_datastore_lead = fields.Integer(string=u"Identifiant de l'opportunité source", copy=False)
    of_send_stage_update = fields.Boolean(string=u"Mis à jour d'étape à envoyer", copy=False)

    @api.model
    def create(self, values):
        # Si l'opportunité vient du connecteur CRM, on renseigne le canal Réseau
        if 'of_datastore_lead' in values:
            values['medium_id'] = self.env.ref('of_datastore_crm_receiver.utm_medium_of_datastore_crm').id
        return super(CrmLead, self).create(values)

    @api.multi
    def write(self, values):
        res = super(CrmLead, self).write(values)

        if 'stage_id' in values:
            self.datastore_update_lead()
        return res

    @api.multi
    def datastore_update_lead(self):
        datastore_crm = self.env['of.datastore.crm.receiver'].search([], limit=1)

        if datastore_crm:
            client = datastore_crm.of_datastore_connect()
            if isinstance(client, basestring):
                # On passe les opportunités en à traiter
                self.write({'of_send_stage_update': True})

            else:
                ds_lead_obj = datastore_crm.of_datastore_get_model(client, 'crm.lead')
                ds_stage_obj = datastore_crm.of_datastore_get_model(client, 'crm.stage')

                for record in self:

                    # On passe l'opportunité en à traiter
                    record.of_send_stage_update = True

                    try:
                        # Si l'opportunité existe dans la base mère
                        lead_ids = datastore_crm.of_datastore_search(
                            ds_lead_obj, [('id', '=', record.of_datastore_lead)])
                        if lead_ids:
                            lead_id = lead_ids[0]

                            # Si l'étape existe dans la base mère
                            stage_ids = datastore_crm.of_datastore_search(
                                ds_stage_obj, [
                                    ('of_crm_stage_id', '=', record.stage_id.of_crm_stage_id),
                                    ('of_crm_stage_id', '!=', False)
                                ])
                            if stage_ids:
                                stage_id = stage_ids[0]
                            else:
                                stage_id = False

                            # On met à jour l'étape
                            datastore_crm.of_datastore_func(ds_lead_obj, 'write', [lead_id, {'stage_id': stage_id}], [])

                            # On ajoute un message dans le mail thread
                            record.message_post(body=u"Opportunité passée en étape %s à la base mère "
                                                   u"via le connecteur CRM." % record.stage_id.name)

                            # On passe l'opportunité en traitée
                            record.of_send_stage_update = False
                    except Exception:
                        pass

    @api.model
    def datastore_leads_to_update(self):
        leads_to_update = self.search([('of_send_stage_update', '=', True)])
        leads_to_update.datastore_update_lead()
