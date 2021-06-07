# -*- coding: utf-8 -*-Je

from odoo import models, fields, api, SUPERUSER_ID


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        update_referred = False
        if self._auto:
            cr.execute(
                    "SELECT * FROM information_schema.columns WHERE table_name = 'res_partner' AND column_name = 'of_referred_id'")
            update_referred = not bool(cr.fetchall())

        super(ResPartner, self)._auto_init()
        if update_referred:
            cr.execute("UPDATE res_partner AS rp "
                       "SET of_referred_id = cl.of_referred_id "
                       "FROM crm_lead AS cl "
                       "WHERE cl.partner_id = rp.id")

    of_referred_id = fields.Many2one('res.partner', string=u"Apporté par", help="Nom de l'apporteur d'affaire")
    of_referee_partner_ids = fields.One2many(
        comodel_name='res.partner', inverse_name='of_referred_id', string=u"Contacts apportés")
    of_referee_lead_ids = fields.One2many(
        comodel_name='crm.lead', inverse_name='of_referred_id', string=u"Opportunités apportées")
    of_referee_count = fields.Integer(string="Nombre de filleuls", compute='_compute_of_referee_count')
    of_referred_reward_id = fields.Many2one('of.referred.reward', string=u"Récompense")
    of_referred_note = fields.Text(string="Notes")
    of_referred_reward_state = fields.Boolean(string="Clos")
    of_referred_reward_date = fields.Date(string=u"Date de récompense")
    of_referred_date = fields.Date(string="Date de parrainage")
    of_referee_date = fields.Date(string=u"Date de dernier parrainage", compute='_compute_of_referee_date', store=True)

    @api.depends('of_referee_partner_ids')
    def _compute_of_referee_count(self):
        for partner in self:
            partner.of_referee_count = len(partner.of_referee_partner_ids)

    @api.depends('of_referee_partner_ids', 'of_referee_partner_ids.of_referred_date')
    def _compute_of_referee_date(self):
        for partner in self:
            if not partner.of_referee_partner_ids.filtered('of_referred_date'):
                continue
            partner.of_referee_date = partner.of_referee_partner_ids.filtered('of_referred_date').\
                sorted('of_referred_date')[-1].of_referred_date

    @api.onchange('of_referred_reward_id')
    def onchange_referred_reward(self):
        if self.of_referred_reward_id and not self.of_referred_reward_date:
            self.of_referred_reward_date = fields.Date.today()

    @api.onchange('of_referred_id')
    def onchange_referred_date(self):
        if self.of_referred_id and not self.of_referred_date:
            self.of_referred_date = fields.Date.today()

    @api.multi
    def name_get(self):
        u""" Permet de renvoyer le nom + magasin + adresse mail + mobile du client quand valeur du """
        u""" contexte 'of_referred' présent """
        name = self._rec_name
        if self._context.get('of_referred') and name in self._fields:
            result = []
            convert = self._fields[name].convert_to_display_name
            for record in self:
                result.append((record.id, ' - '.join([st.strip() for st in
                                                      (convert(record[name], record).strip() or u"Sans nom",
                                                       record.sudo().company_id.name or '', record.email or '',
                                                       record.mobile or '') if st and st.strip()])))
        else:
            result = super(ResPartner, self).name_get()
        return result


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_referred_id = fields.Many2one('res.partner', string=u"Apporté par", help="Nom de l'apporteur d'affaire",
                                     related="partner_id.of_referred_id", readonly=False)
    of_referred_reward_id = fields.Many2one('of.referred.reward', string=u"Récompense",
                                            related="partner_id.of_referred_reward_id", readonly=False)
    of_referred_note = fields.Text(string="Notes", related="partner_id.of_referred_note", readonly=False)
    of_referred_reward_state = fields.Boolean(string="Clos", related="partner_id.of_referred_reward_state",
                                              readonly=False)
    of_referred_reward_date = fields.Date(string=u"Date de récompense", related="partner_id.of_referred_reward_date",
                                          readonly=False)
    of_referred_date = fields.Date(string="Date de parrainage", related="partner_id.of_referred_date", readonly=False)

    @api.onchange('of_referred_reward_id')
    def onchange_referred_reward(self):
        if self.of_referred_reward_id and not self.of_referred_reward_date:
            self.of_referred_reward_date = fields.Date.today()

    @api.onchange('of_referred_id')
    def onchange_referred_date(self):
        if self.of_referred_id and not self.of_referred_date:
            self.of_referred_date = fields.Date.today()


class OfReferredReward(models.Model):
    _name = 'of.referred.reward'
    _order = 'sequence'

    sequence = fields.Integer(string=u"Séquence", default=10)
    name = fields.Char(string=u"Nom de la récompense")
