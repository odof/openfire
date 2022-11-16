# coding: utf-8
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# 1: imports of python lib
# 2: imports of odoo
from odoo import api, models, fields
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib




class ResPartnerBank(models.Model):
    """Ajouter les données sur le mandat SEPA dans les comptes en banque"""
    _inherit = "res.partner.bank"

    @api.model_cr_context
    def _auto_init(self):
        "Basculer les données du mandat SEPA des partenaires vers les comptes en banque"

        # On vérifie si c'est une 1ère mise à jour après la refonte du module (existence du champ of_sepa_rum dans les comptes en banque).
        # Si oui, on bascule les données.
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.columns WHERE table_name = 'res_partner' AND column_name = 'of_sepa_rum'")
        champ_rp = bool(cr.fetchall())
        cr.execute("SELECT * FROM information_schema.columns WHERE table_name = 'res_partner_bank' AND column_name = 'of_sepa_rum'")
        champ_rpb = bool(cr.fetchall())
        res = super(ResPartnerBank, self)._auto_init()
        if champ_rp and not champ_rpb:
            # On copie les champs of_sepa_rum, of_sepa_date_mandat et of_sepa_type_prev de res.partner vers res.partner.bank.
            cr.execute("UPDATE res_partner_bank SET of_sepa_rum = res_partner.of_sepa_rum, of_sepa_date_mandat = res_partner.of_sepa_date_mandat, of_sepa_type_prev = res_partner.of_sepa_type_prev FROM res_partner WHERE res_partner_bank.partner_id = res_partner.id")
        return res

    # On ajoute le champ company_registry (SIRET/SIREN) pour les partenaires.
    # Il est définit dans le module OCA l10n_fr_siret mais on le rajoute au cas où ce module ne serait pas installé.
    of_sepa_rum = fields.Char(u"Référence unique du mandat (RUM) SEPA", size=35, required=False, help=u"Référence unique du mandat (RUM) SEPA pour opérations bancaires par échange de fichiers informatiques")
    of_sepa_date_mandat = fields.Date(u"Date de signature du mandat SEPA", required=False, help=u"Date de signature du mandat SEPA pour opérations bancaires par échange de fichiers informatiques")
    of_sepa_type_prev = fields.Selection(
        [("FRST", u"1er prélèvement récurrent à venir"),
         ("RCUR", u"Prélèvement récurrent en cours"),
         ],
        string=u'Type de prélèvement (SEPA)', required=True, default='FRST',
        help=(u"Type de prélèvement SEPA.\n"
              u"- Mettre à 1er prélèvement quand aucun prélèvement n'a été effectué avec ce mandat.\n"
              u"Lors d'un 1er prélèvement, cette option passera automatiquement à prélèvement récurrent en cours.\n\n"
              u"- Mettre à prélèvement récurrent en cours lorsqu'un prélèvement a déjà été effectué avec ce mandat.\n\n"))

    _sql_constraints = [
        ('unique_of_sepa_rum', 'unique(of_sepa_rum)', u'La référence unique de mandat (RUM) doit être unique')
    ]

    @api.multi
    def action_demande_confirmation_code_rum(self):
        """Action appelée pour générer code RUM"""
        self.ensure_one()

        if self.of_sepa_rum:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'of.generer.code.rum.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_partner_bank_id': self.id,
                },
            }
        else:
            self.generer_code_rum()

        return True

    @api.multi
    def generer_code_rum(self):
        """Action de génération code RUM"""
        self.ensure_one()
        self.of_sepa_rum = self.env['ir.sequence'].next_by_code('of.sepa.rum.seq')
        self.of_sepa_type_prev = 'FRST'

        return True

    def verification_validite(self):
        """Action de vérification des 3 critères de validité"""
        self.ensure_one()

        # Un compte bancaire de type IBAN
        iban = self.acc_type == 'iban'

        # Une séquence RUM unique est définie
        rum_unique = not self.with_context(active_test=False) \
            .search_count([('of_sepa_rum', '=', self.of_sepa_rum), ('id', '!=', self.id)])

        # Une date de SEPA est définie et est antérieure ou égale à la date du contrôle
        date_valide = self.of_sepa_date_mandat and self.of_sepa_date_mandat <= fields.Date.today()

        if iban and rum_unique and date_valide:
            return True
        return False

