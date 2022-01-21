# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_allocated = fields.Many2one('res.partner', u"Affecté à", readonly=True, copy=False)
    of_datastore_sent = fields.Boolean(string=u"Opportunité envoyée via connecteur CRM", copy=False)

    @api.multi
    def action_allocate_lead(self):
        wizard_form = self.env.ref('of_datastore_crm_sender.of_datastore_crm_sender_allocate_wizard_view')

        ctx = dict(
            default_lead_id=self.id,
        )

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.datastore.crm.sender.allocate.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def datastore_send_lead(self):
        self.ensure_one()

        # On vérifie que l'opportunité n'a pas déjà été envoyée
        if self.of_datastore_sent:
            raise UserError(u"L'opportunité a déjà été envoyée par le connecteur !")

        # On vérifie s'il existe un connecteur achat pour ce fournisseur
        datastore_crm = self.env['of.datastore.crm.sender'].search([('partner_id', '=', self.of_allocated.id)], limit=1)

        if datastore_crm:
            client = datastore_crm.of_datastore_connect()
            if isinstance(client, basestring):
                raise UserError(u"Échec de la connexion au connecteur CRM !")

            ds_country_obj = datastore_crm.of_datastore_get_model(client, 'res.country')
            ds_lead_obj = datastore_crm.of_datastore_get_model(client, 'crm.lead')
            ds_stage_obj = datastore_crm.of_datastore_get_model(client, 'crm.stage')

            # On récupère le pays s'il existe déjà sur la base fille
            country_ids = datastore_crm.of_datastore_search(ds_country_obj,  [('name', '=', self.country_id.name)])
            if country_ids:
                country_id = country_ids[0]
            else:
                country_id = False

            stage_id = False
            # On récupère l'étape kanban en fonction du champ of_crm_stage_id
            if self.stage_id:
                stage_ids = datastore_crm.of_datastore_search(
                    ds_stage_obj,
                    [('of_crm_stage_id', '=', self.stage_id.of_crm_stage_id), ('of_crm_stage_id', '!=', False)])
                if stage_ids:
                    stage_id = stage_ids[0]

            values = {
                'of_datastore_lead': self.id,
                'name': self.name,
                'contact_name': self.contact_name,
                'stage_id': stage_id,
                'street': self.street,
                'street2': self.street2,
                'zip': self.zip,
                'city': self.city,
                'country_id': country_id,
                'phone': self.phone,
                'mobile': self.mobile,
                'email_from': self.email_from,
                'description': self.description,
            }

            datastore_crm.of_datastore_create(ds_lead_obj, values)

            # On ajoute un message dans le mail thread
            self.message_post(body=u"Opportunité transmise via le connecteur CRM.")

            self.of_datastore_sent = True
        else:
            raise UserError(u"Aucun connecteur CRM trouvé !")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_network_member = fields.Boolean(string=u"Membre du réseau")
    of_ongoing_lead_count = fields.Integer(
        string=u"Nb. d'opportunités en cours", compute='_compute_of_ongoing_lead_count')

    @api.depends('of_network_member')
    def _compute_of_ongoing_lead_count(self):
        stage_ids = self.env['crm.stage'].search([('probability', '>', 0), ('probability', '>', 0)])
        for partner in self.filtered(lambda p: p.of_network_member):
            partner.of_ongoing_lead_count = self.env['crm.lead'].search_count(
                [
                    ('of_datastore_sent', '=', True),
                    ('of_allocated', '=', partner.id),
                    ('stage_id', 'in', stage_ids.ids)
                ]
            )


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_of_lead_allocation = fields.Boolean(
        string=u"(OF) Affectation d'opportunités", implied_group='of_datastore_crm_sender.group_of_lead_allocation',
        group='base.group_portal,base.group_user,base.group_public')
