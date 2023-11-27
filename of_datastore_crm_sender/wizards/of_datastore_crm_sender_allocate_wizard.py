# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class OfDatastoreCrmAllocateWizard(models.TransientModel):
    _name = 'of.datastore.crm.sender.allocate.wizard'
    _description = u"Wizard d'affectation de partenaire"

    lead_id = fields.Many2one('crm.lead', u"Opportunité", required=True, readonly=True)
    partner_id = fields.Many2one(
        'res.partner', u"Partenaire", domain="[('of_network_member', '=', True)]", required=True)

    def action_done(self):
        if self.partner_id:
            self.lead_id.of_allocated = self.partner_id

            network_members = self.env['of.datastore.crm.network.member'].search(
                [('partner_id', '=', self.partner_id.id)])

            # On vérifie s'il existe un connecteur achat pour ce fournisseur
            connecteur_ids = self.env['of.datastore.crm.sender'].search(
                ['|', '&', ('partner_id', '=', self.partner_id.id), ('is_multicompany', '=', False),
                 '&', ('child_ids', 'in', network_members.ids), ('is_multicompany', '=', True)])

            # Si un connecteur vers une base fille existe pour ce membre réseau,
            # on crée cette opportunité sur la base fille
            if connecteur_ids:
                self.lead_id.datastore_send_lead()
            # Sinon on envoie un mail au membre du réseau
            else:
                template = self.env.ref('of_datastore_crm_sender.of_datastore_crm_sender_email_template')
                template.send_mail(self.lead_id.id)
                self.lead_id.of_datastore_sent = True


class OfDatastoreCrmAutoAllocateWizard(models.TransientModel):
    _name = 'of.datastore.crm.sender.auto.allocate.wizard'
    _description = u"Wizard d'affectation automatique de partenaire"

    lead_ids = fields.Many2many('crm.lead', string=u"Opportunités")
    wizard_line_ids = fields.One2many(
        'of.datastore.crm.sender.auto.allocate.wizard.line', 'wizard_id', string=u"Lignes du wizard")

    @api.onchange('lead_ids')
    def onchange_lead_ids(self):
        of_secteur_obj = self.env['of.secteur']
        res_partner_obj = self.env['res.partner']
        wizard_line_obj = self.env['of.datastore.crm.sender.auto.allocate.wizard.line']

        # On définit le secteur pour les membres réseau si manquant
        membre_reseau_ids = res_partner_obj.search([('of_network_member', '=', True)])
        for membre_reseau in membre_reseau_ids:
            if not membre_reseau.of_secteur_com_id and membre_reseau.zip:
                secteur_id = of_secteur_obj.get_secteur_from_cp(membre_reseau.zip, type_list=['com', 'tech_com'])
                membre_reseau.write({'of_secteur_com_id': secteur_id.id or False})

        # On filtre les opportunités déjà traitées par le connecteur CRM
        for lead in self.lead_ids.filtered(lambda l: not l.of_datastore_sent):

            # On définit le secteur pour le partner de l'opportunité réseau
            if not lead.partner_id.of_secteur_com_id:
                zip = lead.partner_id.zip or lead.zip or False
                of_secteur_com_id = of_secteur_obj.get_secteur_from_cp(zip, type_list=['com', 'tech_com'])
                lead.partner_id.write({'of_secteur_com_id': of_secteur_com_id.id})

            partner_id = False

            if lead.partner_id.of_secteur_com_id:
                # On récupère les partners sur ce secteur, et on les trie par celui qui à moins d'opportunités
                partner_ids = membre_reseau_ids\
                    .filtered(lambda m: m.of_secteur_com_id == lead.partner_id.of_secteur_com_id)\
                    .sorted('of_ongoing_lead_count')

                # On prend le premier s'il existe
                if partner_ids:
                    partner_id = partner_ids[0]

            wizard_line_obj.new({
                'wizard_id': self.id,
                'lead_id': lead.id,
                'partner_id': partner_id,
                'secteur_id': lead.partner_id.of_secteur_com_id.id,
            })

    def action_done(self):
        for line in self.wizard_line_ids:
            if line.partner_id:
                line.lead_id.of_allocated = line.partner_id

                network_members = self.env['of.datastore.crm.network.member'].search(
                    [('partner_id', '=', line.partner_id.id)])

                # On vérifie s'il existe un connecteur achat pour ce fournisseur
                connecteur_ids = self.env['of.datastore.crm.sender'].search(
                    ['|', '&', ('partner_id', '=', line.partner_id.id), ('is_multicompany', '=', False),
                     '&', ('child_ids', 'in', network_members.ids), ('is_multicompany', '=', True)])

                # Si un connecteur vers une base fille existe pour ce membre réseau,
                # on crée cette opportunité sur la base fille
                if connecteur_ids:
                    try:
                        line.lead_id.datastore_send_lead()
                    except Exception:
                        pass

                # Sinon on envoie un mail au membre du réseau
                else:
                    template = self.env.ref('of_datastore_crm_sender.of_datastore_crm_sender_email_template')
                    template.send_mail(line.lead_id.id)
                    line.lead_id.of_datastore_sent = True


class OfDatastoreCrmAutoAllocateWizardLine(models.TransientModel):
    _name = 'of.datastore.crm.sender.auto.allocate.wizard.line'
    _description = u"Ligne de wizard d'affectation automatique de partenaire"

    wizard_id = fields.Many2one('of.datastore.crm.sender.auto.allocate.wizard', u"Wizard")
    lead_id = fields.Many2one('crm.lead', u"Opportunité", readonly=True)
    partner_id = fields.Many2one('res.partner', u"Partenaire", domain="[('of_network_member', '=', True)]")
    secteur_id = fields.Many2one('of.secteur', u"Secteur commercial", readonly=True)
