# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import time
import unicodedata
import re
import base64


class OfAccountPaymentMode(models.Model):
    "Ajouter compte en banque aux modes de paiement"
    _inherit = "of.account.payment.mode"

    bank_id = fields.Many2one('res.partner.bank', u"Compte bancaire", help=u'Compte bancaire pour le mode de paiement.')


class ResCompany(models.Model):
    _inherit = "res.company"

    of_num_nne = fields.Char(u"Numéro national d'émetteur (NNE)", size=6, required=False, help=u"Numéro national d'émetteur pour opérations bancaires par échange de fichiers informatiques")
    of_num_ics = fields.Char(u"Identifiant créancier SEPA (ICS)", size=32, required=False, help=u"Identifiant créancier SEPA (ICS) pour opérations bancaires SEPA par échange de fichiers informatiques")


class ResPartner(models.Model):
    _inherit = "res.partner"

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
    company_registry = fields.Char(u'Registre de la société', size=64)  # Migration : on ajoute le champ company_registry pour les partenaires. Il est définit dans of_sales mais on le rajoute au cas où of_sales ne serait pas installé.

class OfPaiementEdi(models.Model):
    """Paiement par échange de fichier informatique"""
    _name = 'of.paiement.edi'
    _description = u"Effectuer un paiement par échange de fichier informatique"

    @api.model_cr_context
    def _auto_init(self):
        "Vider les anciennes données avant la refonte du module"

        # La table (objet) of_paiement_edi_line n'existait pas avant. Sert de test pour savoir version du module.
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = 'of_paiement_edi' OR table_name = 'of_paiement_edi_line'")
        # S'il n'y a qu'une table (of_paiement_edi sans of_paiement_edi_line), c'est que c'est la version du module avant la refonte qui est installée.
        # On supprime les anciennes données (non affichées avant, uniquement pour historique) pour repartir sur de nouvelles bases
        if len(cr.fetchall()) == 1:
            cr.execute("DELETE FROM of_paiement_edi")
        return super(OfPaiementEdi, self)._auto_init()

    @api.model
    def _default_edi_line_ids(self):
        """Peuple la liste des factures avec celles sélectionnées, ouvertes et qui n'ont pas déjà été envoyées à l'affacturage"""

        facture_vals = [(5, )]  # On efface les lignes existantes
        for facture in self.env['account.invoice'].search([('id', 'in', self._context.get('active_ids', [])),
                                                           ('state', '=', 'open'),
                                                           ('type', 'in', ('out_invoice', 'in_refund'))]):
            values = {
                'invoice_id': facture.id,
                'montant_prelevement': facture.residual,
                'pc_prelevement': (facture.residual * 100.) / facture.amount_total,
                'date_facture': facture.date_invoice,
                'partner': facture.partner_id.name,
                'total_ttc': facture.amount_total,
                'balance': facture.residual,
                'methode_calcul_montant': 'balance'
            }
            facture_vals.append((0, 0, values))
        return facture_vals

    @api.onchange('edi_line_ids')
    def onchange_edi_line_ids(self):
        # Empêcher de générer les paiements si la liste des factures a été modifiée.
        self.aff_bouton_paiement = False

    edi_line_ids = fields.One2many('of.paiement.edi.line', 'edi_id', string=u"Factures sélectionnées à payer", copy=False, default=_default_edi_line_ids)
    date_remise = fields.Date(u'Date de remise du paiement', required=True, default=fields.Datetime.now)
    date_valeur = fields.Date(u'Date de valeur du paiement (LCR)', required=False, default=fields.Datetime.now)
    date_echeance = fields.Date(u"Date d'échéance du paiement", required=True, default=fields.Datetime.now)
    motif = fields.Selection(
        [('nofacture', 'No de facture')], string='Motif opération (SEPA)', required=False,
        help=u"Texte qui apparaît sur le relevé bancaire du débiteur", default='nofacture')
    date_creation = fields.Text('Date de création', default=fields.Datetime.now)
    mode_paiement_id = fields.Many2one('of.account.payment.mode', u'Mode de paiement', required=True)
    mode_paiement = fields.Char(u"Libellé mode de paiement")
    journal_id = fields.Many2one(related='mode_paiement_id.journal_id', string='Journal', store=False)
    sortie = fields.Html('')
    fichier = fields.Binary(u'Télécharger le fichier')
    nom_fichier = fields.Char('Nom du Fichier', size=64, default="edi_" + str(fields.Datetime.now) + ".txt")
    aff_bouton_paiement = fields.Boolean(default=False)
    aff_bouton_genere_fich = fields.Boolean(default=True)
    type_paiement = fields.Char(u'Type de paiement', size=16)
    type_remise_lcr = fields.Selection(
        [("encaissement_forfait", u"Encaissement, crédit forfaitaire après l'échéance"),
         ("encaissement_delai", u"Encaissement, crédit crédit après expiration d'un délai forfaitaire"),
         ("escompte", u"Escompte"),
         ("escompte_valeur", u"Escompte en valeur"),
         ],
        string=u"Type de remise (LCR)", required=False, help=u"Type de remise (LCR uniquement)")
    code_dailly_lcr = fields.Selection(
        [("pas_indication", u"Pas d'indication"),
         ("cession_escompte", u"Cession escompte dans le cadre d'une convention Dailly"),
         ("nantissement", u"Nantissement de créance dans le cadre d'une convention Dailly"),
         ("cession_nantissement", u"Cession ou nantissement hors convention Dailly"),
         ],
        string=u"Convention Dailly (LCR)", required=False, default="pas_indication",
        help=u"Indique si convention Dailly (LCR uniquement).\nChoisir \"Pas d'indication\" si pas de convention.")

    _order = 'date_remise DESC, create_date DESC'

    @api.multi
    def action_paiement_sepa_prev(self):
        self.action_paiement_edi("Pr. SEPA")
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def action_paiement_lcr(self):
        self.action_paiement_edi("LCR")
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def action_paiement_edi(self, type_paiement="Pr. SEPA"):
        """Action appelée pour effectuer un paiement EDI en fonction des factures sélectionnées"""

        self.ensure_one()

        # Teste si au moins une facturé sélectionnée
        if not self.edi_line_ids:
            raise UserError(u"Erreur ! (#ED105)\n\nVous devez sélectionner au moins une facture.")

        # On vérifie qu'il s'agit bien de factures ouvertes non payées
        for edi in self.edi_line_ids:
            if edi.invoice_id.type != 'out_invoice' and edi.invoice_id.type != 'in_refund':
                raise UserError(u"Erreur ! (#ED110)\n\nVous avez sélectionné au moins une facture qui n'est pas une facture client ou un avoir fournisseur.\n\nVous ne pouvez demander le règlement par LCR ou prélèvement SEPA que pour une facture client ou un avoir fournisseur.")
            if edi.invoice_id.state != "open" or edi.invoice_id.residual <= 0 or edi.invoice_id.amount_total <= 0:
                raise UserError(u"Erreur ! (#ED115)\n\nVous avez sélectionné au moins une facture non ouverte, déjà payée ou avec une balance ou un montant total négatif.\nVous ne devez sélectionner que des factures ouvertes, non payées avec une balance et un montant total positif.")

        # On récupère le mode de paiement et génère le fichier EDI
        if type_paiement == "LCR":
            self.genere_fichier_lcr(self.edi_line_ids)
        else:
            self.genere_fichier_sepa_prev(self.edi_line_ids)

        return True

    @api.model
    def _get_partner_rib(self, partner):
        rib_obj = self.env['res.partner.bank']
        rib = False
        while partner and not rib:
            rib = rib_obj.search([('partner_id', '=' , partner.id)])
            partner = partner.parent_id
        return rib

    @api.multi
    def genere_fichier_lcr(self, liste_factures):
        """Génère le fichier pour lettre de change relevé (LCR)"""
        no_ligne = 1  # No de la ligne du fichier généré
        nb_facture = 0  # Nombre de facture à acquitter (pas celles montant = 0)
        chaine = ""  # Contient la chaine du fichier généré
        montant_total = 0

        # 1ère ligne : émetteur
        sortie = u"<b>Tireur :</b>\n<ul>\n<li>" + self.mode_paiement_id.company_id.name + " ["
        chaine += "0360"
        chaine += str(no_ligne).zfill(8)            # No de la ligne (no enregistrement sur 8 caractères)
        if self.mode_paiement_id.company_id.of_num_nne:  # No émetteur
            if len(self.mode_paiement_id.company_id.of_num_nne) > 6:
                raise UserError(u"Erreur ! (#ED205)\n\nLe n° national d'émetteur de l'émetteur (" + self.mode_paiement_id.company_id.name + u") dépasse 6 caractères.")
            chaine += self.chaine2ascii_taille_fixe_maj(self.mode_paiement_id.company_id.of_num_nne, 6)
        else:
            chaine += " " * 6
        chaine += " " * 6                           # Type convention (6 caractères)
        if self.date_remise:                        # Date de remise (6 caractères)
            chaine += self.date_remise[8:10]+self.date_remise[5:7]+self.date_remise[2:4]
        else:
            chaine += " " * 6
        chaine += self.chaine2ascii_taille_fixe_maj(self.mode_paiement_id.company_id.name, 24)  # Raison sociale de l'émetteur en majuscule sans accent et ponctuation interdite tronquée ou complétée à 24 caractères
        if self.mode_paiement_id.bank_id.bank_id.name:                        # Domiciliation (nom) bancaire du tirant
            chaine += self.chaine2ascii_taille_fixe_maj(self.mode_paiement_id.bank_id.bank_id.name, 24)
            sortie += self.mode_paiement_id.bank_id.bank_id.name

        # Code entrée (Type remise)
        if self.type_remise_lcr == 'encaissement_forfait':
            chaine += "3"
        elif self.type_remise_lcr == 'encaissement_delai':
            chaine += "4"
        elif self.type_remise_lcr == 'escompte':
            chaine += "1"
        elif self.type_remise_lcr == 'escompte_valeur':
            chaine += "2"
        else:
            raise UserError(u"Erreur ! (#ED207)\n\nVous devez choisir le type de remise (LCR).")

        # Code Daily
        if self.code_dailly_lcr == 'pas_indication':
            chaine += "0"
        elif self.code_dailly_lcr == 'cession_escompte':
            chaine += "1"
        elif self.code_dailly_lcr == 'nantissement':
            chaine += "2"
        elif self.code_dailly_lcr == 'cession_nantissement':
            chaine += "3"
        else:
            raise UserError(u"Erreur ! (#ED208)\n\nVous devez choisir s'il y a une convention Dailly (LCR).\nChoisir \"Pas d'indication\" si pas de convention.")

        # code monnaie (euro)
        chaine += "E"

        # Référence bancaire émetteur - Configuré dans Odoo soit en IBAN
        temp = self.mode_paiement_id.bank_id.acc_number
        if temp:
            temp = temp.replace("IBAN", "").replace(" ", "").upper()
        if temp and len(temp) == 27 and temp[0:2] == "FR":  # Si IBAN renseigné et français, on se base dessus
            chaine += temp[4:9]     # Code banque
            sortie += u" Banque : " + temp[4:9]
            chaine += temp[9:14]    # Code guichet
            sortie += u" Guichet : " + temp[9:14]
            chaine += temp[14:25]   # No compte
            sortie += u" Compte : " + temp[14:25]
        else:   # Si pas français, on ne peut pas faire de LCR car doit être un être un compte au (ancien) format RIB code banque, guichet, compte, clé.
            raise UserError(u"Erreur ! (#ED210)\n\nPas de coordonnées bancaires (IBAN) françaises valides trouvées pour le mode de paiement " + self.mode_paiement_id.name + u".\n\nPour effectuer une LCR, il faut obligatoirement des coordonnées bancaires françaises.")
        sortie += "]"
        chaine += " " * 16            # Zone réservée
        if self.date_valeur:          # Date de valeur
            chaine += self.date_valeur[8:10]+self.date_valeur[5:7]+self.date_valeur[2:4]
        else:
            chaine += " " * 6
        chaine += " " * 10  # Zone réservée

        # Avant 03/01/2019 temp = liste_factures[0].company_id.company_registry    # No SIREN
        temp = self.mode_paiement_id.company_id.company_registry    # No SIREN
        if not temp:
            chaine += " " * 15
        else:
            if len(temp.replace(" ", "")) == 14:   # C'est un n° SIRET. Le SIREN est les 9 premiers chiffres.
                temp = temp.replace(" ", "")[0:9]
            elif len(temp) > 15:
                raise UserError(u"Erreur ! (#ED215)\n\nLe n° SIREN de la société " + self.mode_paiement_id.company_id.name + u" dépasse 15 caractères.")
            chaine += temp.ljust(15, " ")
            sortie += u" No SIREN : " + temp
        chaine += " " * 11  # Référence remise à faire
        chaine += "\n"
        sortie += "</li></ul>\n"

        # 2e ligne : tiré(s)
        sortie += u"<b>Tiré(s) :</b>\n<ul>\n"
        for facture in liste_factures:
            sortie += u"<li>"
            montant_du = facture.montant_prelevement
            # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la facture suivante
            if montant_du == 0:
                sortie += u"<b>Facture non exigible</b> : " + facture.invoice_id.partner_id.display_name + u" [Montant total facture : " + str('%.2f' % facture.total_ttc).replace('.', ',') + u" euros]</li>\n"
                continue
            elif montant_du < 0:
                raise UserError(u"Erreur ! (#ED217)\n\nLa balance de la facture de " + facture.invoice_id.partner_id.display_name + u" est négative.\n\nVous ne pouvez payer par LCR que des factures avec un solde positif.")
            else:
                nb_facture = nb_facture + 1

            sortie += facture.invoice_id.partner_id.display_name + " ["
            rib = self._get_partner_rib(facture.invoice_id.partner_id)
            if not rib:
                raise UserError(u"Erreur ! (#ED220)\n\nPas de compte bancaire trouvé pour " + facture.invoice_id.partner_id.display_name + u".\n\nPour effectuer une LCR, un compte en banque doit être défini pour le client de chaque facture.")
            no_ligne = no_ligne + 1
            chaine += "0660"
            chaine += str(no_ligne).zfill(8)        # No de la ligne (no enregistrement sur 8 caractères)
            chaine += " " * 8                       # Zones réservées
            chaine += " " * 10                      # Référence du tiré
            chaine += self.chaine2ascii_taille_fixe_maj(facture.invoice_id.partner_id.display_name, 24)  # Nom du tiré (24 caractères)
            if rib[0].bank_name:                    # Domiciliation (nom) bancaire du tiré
                chaine += self.chaine2ascii_taille_fixe_maj(rib[0].bank_name, 24)
                sortie += rib[0].bank_name
            else:
                chaine += " " * 24
            chaine += "0"                           # Acceptation
            chaine += " " * 2                       # Zone réservée

            # Référence bancaire - Configuré dans Odoo en IBAN
            temp = rib[0].acc_number
            if temp:
                temp = temp.replace("IBAN", "").replace(" ", "").upper()  # Suppression de possibles caractères superflus
            if temp and len(temp) == 27 and temp[0:2] == "FR":  # Si IBAN renseigné et français, on se base dessus
                chaine += temp[4:9]     # Code banque
                sortie += " Banque : " + temp[4:9]
                chaine += temp[9:14]    # Code guichet
                sortie += " Guichet : " + temp[9:14]
                chaine += temp[14:25]   # No compte
                sortie += " Compte : " + temp[14:25]
            else:   # Aucune référence bancaire valide
                raise UserError(u"Erreur ! (#ED225)\n\nPas de coordonnées bancaires (RIB ou IBAN) valides trouvées pour " + facture.invoice_id.partner_id.display_name + u".\n\n (Seuls les comptes IBAN français sont autorisés, FR suivi de 25 chiffres)")
            sortie += "]"
            montant_total = montant_total + montant_du
            sortie += " - <b>Montant : " + str('%.2f' % montant_du).replace('.', ',') + " euros</b>"
            chaine += str('%.2f' % montant_du).replace('.', '').zfill(12)  # Montant
            chaine += " " * 4                       # Zone réservée
            chaine += self.date_echeance[8:10]+self.date_echeance[5:7]+self.date_echeance[2:4]    # Date d'échéance
            chaine += self.date_creation[8:10]+self.date_creation[5:7]+self.date_creation[2:4]    # Date de création
            chaine += " " * 4                       # Zone réservée
            chaine += " "                           # Type
            chaine += " " * 3                       # Nature
            chaine += " " * 3                       # Pays
            temp = facture.invoice_id.partner_id.company_registry or facture.invoice_id.partner_id.commercial_partner_id.company_registry    # No SIREN
            if not temp:
                chaine += " " * 9
            else:
                if len(temp.replace(" ", "")) == 14:   # C'est un n° SIRET. Le SIREN est les 9 premiers chiffres.
                    temp = temp.replace(" ", "")[0:9]
                elif len(temp) > 9:
                    raise UserError(u"Erreur ! (#ED230)\n\nLe n° SIREN de " + facture.invoice_id.partner_id.display_name + u" dépasse 9 caractères.")
                chaine += temp.ljust(9, " ")
                sortie += " - [No SIREN : " + temp + "]"
            chaine += " " * 10                       # Référence tireur
            chaine += "\n"
            sortie += "</li>\n"
        sortie += "</ul>\n"

        # Dernière ligne : total
        no_ligne = no_ligne + 1
        chaine += "0860"
        chaine += str(no_ligne).zfill(8)            # No de la ligne (no enregistrement sur 8 caractères)
        chaine += " " * 90                          # Zones réservées
        sortie += u"<b>Montant total : " + str('%.2f' % montant_total).replace('.', ',') + " euros</b><br>\n"
        chaine += str('%.2f' % montant_total).replace('.', '').zfill(12)  # Montant total
        chaine += " " * 46                          # Zones réservées
        chaine += "\n"

        if nb_facture:  # Si des factures sont à payer, on génère le fichier
            sortie = u"<p>Pour enregistrer l'opération et obtenir le fichier à transmettre à la banque, <b><u>vous devez valider le paiement des factures</u></b>.</p>\n<p>Le fichier lettre change relevé (LCR) a été généré avec les éléments suivants :</p>\n" + sortie
            chaine = base64.encodestring(chaine)
            self.write({
                'fichier': chaine,
                'nom_fichier': "lcr_" + time.strftime('%Y-%m-%d_%H%M%S') + ".txt",
                'type_paiement': 'LCR',
                'aff_bouton_paiement': True
            })
        else:
            sortie = u"<p>Aucune facture à payer. Le fichier n'a pas été généré.</p>\n" + sortie
            self.write({'aff_bouton_paiement': False})

        self.write({
            'date_creation': time.strftime('%Y-%m-%d %H:%M:%S'),
            'sortie': sortie
        })
        return True

    @api.multi
    def genere_fichier_sepa_prev(self, liste_factures):
        """Génère le fichier pour le prélèvement SEPA"""
        sortie = ""
        chaine_transaction = ""  # Contient la chaine du fichier généré
        chaine_entete = ""
        chaine_lot = ""
        montant_total = 0
        montant_total_lot = 0
        nb_transaction = 0
        nb_transaction_lot = 0
        index = 1  # Pour générer des identifiants uniques

        # On doit faire un lot par type de prélèvement (frst, rcur, ...)
        # On classe la liste des factures par type de prélèvement
        factures_par_type = {}
        for facture in liste_factures:
            if not facture.invoice_id.partner_id.of_sepa_type_prev:
                raise UserError(u"Erreur ! (#ED431)\n\nLe champ \"Type de prélèvement SEPA\" n'a pas été configuré pour " + facture.invoice_id.partner_id.display_name + u".\n\nCe champ est obligatoire pour effectuer un prélèvement SEPA et se configure dans l'onglet Achats-Ventes du client.")
            if facture.invoice_id.partner_id.of_sepa_type_prev not in ('FRST', 'RCUR'):
                raise UserError(u"Erreur ! (#ED432)\n\nLe champ \"Type de prélèvement SEPA\" contient une valeur incorrecte pour " + facture.invoice_id.partner_id.display_name + u".\n\nVeuillez configurer ce champ à nouveau. Il se configure dans l'onglet Achats-Ventes du client.")
            if facture.invoice_id.partner_id.of_sepa_type_prev not in factures_par_type:
                factures_par_type[facture.invoice_id.partner_id.of_sepa_type_prev] = []
            factures_par_type[facture.invoice_id.partner_id.of_sepa_type_prev].append(facture)

        sortie += u"<b>Tiré(s) :</b>\n<ul>\n"
        # On parcourt la liste des factures
        # par type de prélèvement
        for type_prev in factures_par_type:
            # sur chaque facture d'un type
            for facture in factures_par_type[type_prev]:
                montant_du = facture.montant_prelevement

                # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la facture suivante
                if montant_du == 0:
                    sortie += u"<li><b>Facture non exigible</b> : " + facture.invoice_id.partner_id.display_name + u" [Montant total facture : " + str('%.2f' % facture.total_ttc).replace('.', ',') + u" euros]</li>\n"
                    continue
                elif montant_du < 0:
                    raise UserError(u"Erreur ! (#ED434)\n\nLa balance de la facture de " + facture.invoice_id.partner_id.display_name + u" est négative.\n\nVous ne pouvez payer par prélèvement SEPA que des factures avec un solde positif.")

                # On récupère les coordonnées bancaires
                rib = self._get_partner_rib(facture.invoice_id.partner_id)
                if not rib:
                    raise UserError(u"Erreur ! (#ED436)\n\nPas de compte bancaire trouvé pour " + facture.invoice_id.partner_id.display_name + u".\n\nPour effectuer une opération SEPA, un compte en banque doit être défini pour le client de chaque facture.")
                chaine_transaction += """
                        <!-- Niveau transaction -->
                        <DrctDbtTxInf> <!-- Débit à effectuer (plusieurs possible) -->
                            <PmtId>
                                <EndToEndId>PREV""" + time.strftime('%S%M%H%d%m%Y') + str(index) + """</EndToEndId> <!-- Identifiant de transaction envoyé au débiteur obligatoire -->
                            </PmtId>
                            <InstdAmt Ccy="EUR">""" + str('%.2f' % montant_du)
                index = index + 1
                chaine_transaction += """</InstdAmt> <!-- Montant de la transaction obligatoire -->
                            <DrctDbtTx>
                                <MndtRltdInf> <!-- Informations relatives au mandat -->
                                    <MndtId>"""
                if facture.invoice_id.partner_id.of_sepa_rum:
                    chaine_transaction += str(facture.invoice_id.partner_id.of_sepa_rum)
                else:
                    raise UserError(u"Erreur ! (#ED438)\n\nPas de référence unique du mandat (RUM) trouvé pour " + facture.invoice_id.partner_id.display_name + u".\n\nLe RUM est obligatoire pour effectuer un prélèvement SEPA et se configure dans l'onglet Achats-Ventes du client.")
                chaine_transaction += """</MndtId> <!-- Code RUM -->
                                    <DtOfSgntr>"""
                if facture.invoice_id.partner_id.of_sepa_date_mandat:
                    chaine_transaction += str(facture.invoice_id.partner_id.of_sepa_date_mandat)
                else:
                    raise UserError(u"Erreur ! (#ED440)\n\nPas de date de signature du mandat SEPA trouvé pour " + facture.invoice_id.partner_id.display_name + u".\n\nCette date est obligatoire pour effectuer un prélèvement SEPA et se configure dans l'onglet Achats-Ventes du client.")
                chaine_transaction += """</DtOfSgntr> <!-- Date de signature du mandat -->
                                    <AmdmntInd>false</AmdmntInd> <!-- facultatif Indicateur permettant de signaler une modification d'une ou plusieurs données du mandat. Valeurs : "true" (si il y a des modifications) "false" (pas de modification). Valeur par défaut : "false" -->
                                </MndtRltdInf>
                            </DrctDbtTx>
                            <DbtrAgt> <!-- Référence banque débiteur -->
                                <FinInstnId>
                                    <BIC>"""
                if rib[0].bank_id.bic:
                    chaine_transaction += str(rib[0].bank_id.bic)
                else:
                    raise UserError(u"Erreur ! (#ED445)\n\nPas de code BIC (SWIFT) de la banque trouvé pour " + facture.invoice_id.partner_id.display_name + u".\n\nIl est nécessaire de fournir ce code pour effectuer une opération SEPA.")
                chaine_transaction += """</BIC> <!-- Code SWIFT banque débiteur -->
                                </FinInstnId>
                            </DbtrAgt>
                            <Dbtr> <!-- Information sur le débiteur obligatoire mais balises filles facultatives-->
                                <Nm>""" + self.chaine2ascii_taillemax(facture.invoice_id.partner_id.display_name, 70) + """</Nm> <!-- Nom débiteur -->
                            </Dbtr>
                            <DbtrAcct> <!-- Informations sur le compte à débiter obligatoire -->
                                <Id>
                                    <IBAN>"""
                if rib[0].acc_number:
                    chaine_transaction += str(rib[0].acc_number).replace("IBAN", "").replace(" ", "").upper()
                else:
                    raise UserError(u"Erreur ! (#ED450)\n\nPas d'IBAN valide trouvé pour " + facture.invoice_id.partner_id.display_name + u".\n\nIl est nécessaire d'avoir des coordonnées bancaires sous forme d'IBAN pour effectuer une opération SEPA.")
                chaine_transaction += """</IBAN>
                                </Id>
                            </DbtrAcct>"""
                if self.motif:    # On insère le motif
                    if self.motif == 'nofacture' and facture.invoice_id.number:
                        chaine_transaction += """
                            <RmtInf> <!-- Information sur la remise de la transaction obligatoire -->
                                <Ustrd>Facture """ + self.chaine2ascii_taillemax(facture.invoice_id.number, 140) + """</Ustrd> <!-- Libellé apparaissant sur le relevé du débiteur -->
                            </RmtInf>"""
                chaine_transaction += """
                        </DrctDbtTxInf>
                        <!-- Fin niveau transaction -->"""
                nb_transaction = nb_transaction + 1
                nb_transaction_lot = nb_transaction_lot + 1
                montant_total = montant_total + montant_du
                montant_total_lot = montant_total_lot + montant_du
                sortie += u"<li>" + facture.invoice_id.partner_id.display_name + " ["
                if rib[0].bank_name:
                    sortie += rib[0].bank_name + " "
                sortie += u"BIC : " + rib[0].bank_bic + u" IBAN : " + str(rib[0].acc_number).upper() + u"] - <b>Montant : " + str('%.2f' % montant_du).replace('.', ',') + u" euros</b></li>\n"
                # Fin parcours chaque facture d'un type

            # Si pas de facture à payer en fonction de l'échéancier dans ce lot, on passe au lot suivant
            if nb_transaction_lot == 0:
                continue

            # On génére le lot
            chaine_lot += """
                <!-- Lot de transaction -->
                <PmtInf> <!-- Instructions de prélèvements obligatoire au moins une fois-->
                    <PmtInfId>LOT""" + time.strftime('%S%M%H%d%m%Y') + str(index) + """</PmtInfId> <!-- Identifiant du lot de transactions Peut être la même valeur que GrpHdr si un seul lot de transaction obligatoire -->
                    <PmtMtd>DD</PmtMtd> <!-- Méthode de paiement obligatoire -->
                    <NbOfTxs>""" + str(nb_transaction_lot) + """</NbOfTxs> <!-- Nb de transaction du lot facultatif -->
                    <CtrlSum>""" + str('%.2f' % montant_total_lot) + """</CtrlSum> <!-- Cumul des sommes des transactions du lot facultatif -->
                    <PmtTpInf> <!-- Information sur le type de paiement Normalement facultatif mais certaines banques attendent cet élément -->
                        <SvcLvl> <!-- Niveau de service -->
                            <Cd>SEPA</Cd> <!-- Contient la valeur SEPA -->
                        </SvcLvl>
                        <LclInstrm>
                            <Cd>CORE</Cd> <!-- CORE pour les débits avec une personne physique, B2B pour les débits entre entreprises -->
                        </LclInstrm>
                        <SeqTp>""" + str(type_prev) + """</SeqTp> <!-- Type de séquence : OOFF pour un débit ponctuel, FIRST pour un 1er débit régulier, RCUR pour un débit régulier récurrent, FINAL pour un dernier débit récurrent -->
                    </PmtTpInf>
                    <ReqdColltnDt>""" + self.date_echeance + """</ReqdColltnDt> <!-- Date d'échéance -->
                    <Cdtr> <!-- Information sur le créancier -->
                        <Nm>""" + self.chaine2ascii_taillemax(self.mode_paiement_id.company_id.name, 70) + """</Nm> <!-- Nom du créancier facultatif -->
                    </Cdtr>
                    <CdtrAcct> <!-- Information du compte du créditeur -->
                        <Id> <!-- Peut aussi contenir balise CCy pour monnaie au format ISO -->
                            <IBAN>"""
            index = index + 1
            if self.mode_paiement_id.bank_id.acc_number:
                chaine_lot += str(self.mode_paiement_id.bank_id.acc_number).replace("IBAN", "").replace(" ", "").upper()
            else:
                raise UserError(u"Erreur ! (#ED420)\n\nPas d'IBAN valide trouvé pour le mode de paiement " + self.mode_paiement_id.name + u".\n\nIl est nécessaire d'avoir des coordonnées bancaires sous forme d'IBAN pour effectuer une opération SEPA.")
            chaine_lot += """</IBAN>
                        </Id>
                    </CdtrAcct>
                    <CdtrAgt> <!-- Banque du créancier -->
                        <FinInstnId>
                            <BIC>"""
            if self.mode_paiement_id.bank_id.bank_bic:
                chaine_lot += str(self.mode_paiement_id.bank_id.bank_bic)
            else:
                raise UserError(u"Erreur ! (#ED425)\n\nPas de code BIC (SWIFT) de la banque attachée au mode de paiement " + self.mode_paiement_id.name + u".\n\nIl est nécessaire de fournir ce code pour effectuer une opération SEPA.")
            chaine_lot += """</BIC> <!-- Code SWIFT de la banque facultatif -->
                        </FinInstnId>
                    </CdtrAgt>
                    <ChrgBr>SLEV</ChrgBr> <!-- Valeur fixe SLEV -->
                    <CdtrSchmeId> <!-- Identification du créancier -->
                        <Id>
                            <PrvtId>
                                <Othr>
                                    <Id>"""
            if self.mode_paiement_id.company_id.of_num_ics:
                chaine_lot += str(self.mode_paiement_id.company_id.of_num_ics)
            else:
                raise UserError(u"Erreur ! (#ED430)\n\nPas d'identifiant créancier SEPA (ICS) trouvé pour l'émetteur (" + self.mode_paiement_id.company_id.name + u").\n\nCet identifiant est obligatoire pour effectuer un prélèvement SEPA et se configure dans configuration/société/" + self.mode_paiement_id.company_id.name + ".")
            chaine_lot += """</Id> <!-- Identifiant du créancier ICS -->
                                    <SchmeNm>
                                        <Prtry>SEPA</Prtry> <!-- De valeur fixe SEPA -->
                                    </SchmeNm>
                                </Othr>
                            </PrvtId>
                        </Id>
                    </CdtrSchmeId>"""
            # On ajoute les transactions
            chaine_lot = chaine_lot + chaine_transaction + """
                </PmtInf>
                <!-- Fin lot de transaction -->
            """
            montant_total_lot = 0
            nb_transaction_lot = 0
            chaine_transaction = ""
            # Fin parcours par type

        # Fin parcours de toutes les factures
        sortie += u"</ul>\n"

        # On ajoute l'en-tête.
        chaine_entete += """<?xml version="1.0" encoding="utf-8"?>
        <Document xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">
            <CstmrDrctDbtInitn>
                <GrpHdr> <!-- En tête -->
                    <MsgId>MES""" + time.strftime('%S%M%H%d%m%Y') + str(index) + """</MsgId> <!-- Identifiant unique du message M -->
                    <CreDtTm>""" + str(self.date_creation).replace(' ', 'T') + """</CreDtTm>    <!-- Date de création au format ISO M -->
                    <NbOfTxs>""" + str(nb_transaction) + """</NbOfTxs>    <!-- Nb total de transactions dans le fichier M -->
                    <CtrlSum>""" + str('%.2f' % montant_total) + """</CtrlSum> <!-- somme totale des transactions point pour décimale -->
                    <InitgPty>    <!-- élément de type Partyidentification32 Partie initiatrice de la transaction peut contenir nom créancier adresse Obligatoire mais peut être vide -->
                        <Nm>""" + self.chaine2ascii_taillemax(self.mode_paiement_id.company_id.name, 70) + """</Nm>
                    </InitgPty>
                </GrpHdr>
                <!-- Fin en-tête -->
                """
        index = index + 1
        # On met l'en-tête de début et les balises de fin
        chaine = chaine_entete + chaine_lot + """
            </CstmrDrctDbtInitn>
        </Document>"""

        sortie += u"<b>Montant total : " + str('%.2f' % montant_total).replace('.', ',') + " euros</b><br>\n"
        sortie = "BIC : " + str(self.mode_paiement_id.bank_id.bank_bic) + " IBAN : " + str(self.mode_paiement_id.bank_id.acc_number).upper() + "]</li>\n</ul>\n" + sortie
        if self.mode_paiement_id.bank_id.bank_name:
            sortie = self.mode_paiement_id.bank_id.bank_name + " " + sortie

        sortie = "<b>Tireur :</b>\n<ul>\n<li>" + self.mode_paiement_id.company_id.name + " [" + sortie

        if nb_transaction:  # Si des factures sont à payer, on génère le fichier
            sortie = u"<p>Pour enregistrer l'opération et obtenir le fichier à transmettre à la banque, <b><u>vous devez valider le paiement des factures</u></b>.</p>\n<p>Le fichier prélèvement SEPA a été généré avec les éléments suivants :</p>\n" + sortie
            chaine = base64.encodestring(chaine)
            self.write({
                'fichier': chaine,
                'nom_fichier': u"prélèvements_sepa_" + time.strftime('%Y-%m-%d_%H%M%S') + ".txt",
                'type_paiement': 'Pr. SEPA',
                'aff_bouton_paiement': True
            })
        else:
            sortie = u"<p>Aucune facture à payer. Le fichier n'a pas été généré.</p>\n" + sortie
            self.write({'aff_bouton_paiement': False, 'fichier': ''})

        self.write({
            'date_creation': time.strftime('%Y-%m-%d %H:%M:%S'),
            'sortie': sortie
        })

        return True

    # Fonction en OpenERP 6.1 : conservé pour archive. À migrer quand échéancier instauré pour les factures en Odoo 10.0
    # @api.model
    # def montantapayer_echeancier(self, facture):
    #     """calcul le montant à payer en fonction de l'échéancier de la facture"""
    #     result = 0
    #     date_aujourdhui = self.date_creation[0:10]
    #
    #     if facture.residual: # montant acquitté = montant déjà payé d'après balance (total facture moins ce qui reste à payer)
    #         montant_acquitte = facture.amount_total - facture.residual
    #     else:
    #         montant_acquitte = 0
    #
    #     # Si pas de ligne dans l'échéancier, on considère que la facture est à payer au comptant (échéance = date facture)
    #     if not facture.acompte_line_ids:
    #         if facture.date_invoice and date_aujourdhui >= facture.date_invoice: # Si date de facture existe et est avant la date d'échéance on doit payer le montant total
    #             if facture.residual:
    #                 result = facture.residual
    #             else:
    #                 result = facture.amount_total
    #         else: # La date de la facture est après aujourd'hui, rien à payer
    #             result = 0
    #     else:
    #         cumul_montant_echeance = 0
    #         # On parcourt les lignes de l'échéancier jusqu'à la date de l'exécution de l'ordre pour déterminer le montant cumulé des échéances à ce jour.
    #         for echeance in facture.acompte_line_ids:
    #             if self.date_echeance < echeance.date:
    #                 break
    #             cumul_montant_echeance = cumul_montant_echeance + echeance.montant
    #
    #         result = cumul_montant_echeance - montant_acquitte
    #
    #     if result < 0:
    #         result = 0
    #     return result

    @api.multi
    def action_enregistre_paiements(self):
        """Enregistre les paiements des factures suite à un paiement EDI"""
        sortie = ""
        if not self.aff_bouton_paiement:
            raise UserError(u"Erreur ! (#ED303)\n\nVous avez modifié la liste des factures depuis la dernière génération du fichier de paiements.\n\nRegénérez une nouvelle fois le fichier avant d'effectuer une nouvelle validation des paiements.")

        for edi_ligne in self.edi_line_ids:

            montant_du = edi_ligne.montant_prelevement

            # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la facture suivante
            if montant_du == 0:
                continue

            # On vérifie que le solde de la facture n'a pas changé entre la génération du fichier et la validation du paiement.
            # On vérifie que le montant à payer n'est pas supérieur au solde la facture.
            if montant_du > edi_ligne.invoice_id.residual:
                raise UserError(u"Erreur ! (#ED305)\n\nLe montant à payer pour la facture " + edi_ligne.invoice_id.number + u" est supérieur au restant dû.\n\nLes paiements de cette facture ont dû changer depuis la génération du fichier.\n\nRectifiez le montant à prélever et générez à nouveau le fichier avant de valider les paiements.")

            # On crée le paiement.
            payment = self.env['account.payment'].create({
                'invoice_ids': [(6, 0, [edi_ligne.invoice_id.id])],
                'amount': montant_du,
                'payment_date': self.date_remise,
                'communication': '',
                'partner_id': edi_ligne.invoice_id.partner_id.id,
                'partner_type': edi_ligne.invoice_id.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
                'journal_id': self.mode_paiement_id.journal_id.id,
                'payment_type': 'inbound',
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'payment_difference_handling': 'open',
                'writeoff_account_id': False,
                'of_payment_mode_id': self.mode_paiement_id.id,
            })

            if not payment:
                raise UserError(u"Erreur ! (#ED310)\n\nErreur création du paiement pour la facture du " + edi_ligne.invoice_id.date_invoice + u", client : " + edi_ligne.invoice_id.partner_id.display_name + u", montant restant à payer : " + str('%.2f' % montant_du).replace('.', ',') + u" euros.\n\nAucun paiement n'a été en conséquence validé.")
            payment.post()  # On le confirme.

            # Si c'est un prélèvement SEPA, on met le champ type de prélèvement SEPA de chaque client à récurrent en cours si était à 1er prélèvement à venir
            if self.type_paiement == 'Pr. SEPA' and edi_ligne.invoice_id.partner_id.of_sepa_type_prev == 'FRST':
                if not edi_ligne.invoice_id.partner_id.write({'of_sepa_type_prev': 'RCUR'}):
                    raise UserError(u"Erreur ! (#ED320)\n\nErreur dans l'enregistrement du type de prélèvement SEPA pour : " + edi_ligne.invoice_id.partner_id.display_name + u".\n\nAucun paiement n'a été en conséquence validé.")

        sortie = u"<p>Le paiement des factures a été effectué.</p>\n<p>Il vous reste à transmettre le fichier à votre banque.</p>\n<p>-----------------------------------------------</p>\n" + sortie

        if self.sortie:   # On récupère la sortie d'avant si elle existe
            sortie = sortie + self.sortie
        self.write({
            'sortie': sortie,
            'aff_bouton_paiement': False,
            'aff_bouton_genere_fich': False
        })
        return {'type': 'ir.actions.do_nothing'}

    def chaine2ascii_taille_fixe_maj(self, chaine, longueur):
        """ (pour LCR) Retourne la chaine en majuscule sans accent et ponctuation autre que ().,/+-:*espace et tronquée ou complétée à (longueur) caractères"""
        if not chaine or not longueur or longueur < 1:
            return False
        chaine = unicodedata.normalize('NFKD', chaine).encode('ascii', 'ignore')
        chaine = re.sub(r'[^0-9A-Za-z\(\)\ \.\,\/\+\-\:\*]', ' ', chaine)
        chaine = chaine[:longueur]
        return chaine.upper().ljust(longueur)

    def chaine2ascii_taillemax(self, chaine, longueur):
        """ (pour SEPA) Retourne la chaine sans accent et ponctuation autre que /-?:().,‟espace et tronquée à (longueur) caractères"""
        if not chaine or not longueur or longueur < 1:
            return False
        chaine = unicodedata.normalize('NFKD', chaine).encode('ascii', 'ignore')
        chaine = re.sub(r'[^0-9A-Za-z\(\)\ \.\,\/\?\-\:]', ' ', chaine)
        return chaine[:longueur]


class OfPaiementEdiLine(models.Model):
    """Factures à payer par EDI"""
    _name = 'of.paiement.edi.line'
    _description = u"Factures à payer par EDI"

    invoice_id = fields.Many2one('account.invoice', string="Facture", required=True, domain="['&', ('state','=','open'), ('residual','>',0),('type','in',('out_invoice','in_refund'))]")
    edi_id = fields.Many2one('of.paiement.edi', 'EDI')
    date_facture = fields.Date(u'Date facture', related='invoice_id.date_invoice', readonly=True)
    partner = fields.Char(string=u'Partenaire', related='invoice_id.partner_id.name', readonly=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    montant_prelevement = fields.Monetary(string=u'Montant à prélever')
    total_ttc = fields.Monetary(string=u'Total TTC', related='invoice_id.amount_total', readonly=True)
    balance = fields.Monetary(string=u'Montant dû', related='invoice_id.residual', readonly=True)
    pc_prelevement = fields.Float(string=u'% du montant TTC de la facture à prélever')
    methode_calcul_montant = fields.Selection(
        [('balance', u'montant restant dû'),
         ('fixe', u'montant fixe'),
         ('pc', u'% du montant TTC de la facture'),
         ],
        default='balance',
        string=u"Mode calcul du montant à prélever",
        required=True,
        help=u"Détermine comment est calculée le montant à prélever")

    _sql_constraints = [
        ('invoice_edi_uniq', 'unique (invoice_id, edi_id)', u'Erreur : une même facture a été saisie plusieurs fois dans la liste des factures à payer.')
    ]

    @api.onchange('methode_calcul_montant', 'pc_prelevement', 'montant_prelevement', 'invoice_id')
    def onchange_montant_prelevement(self):
        if self.methode_calcul_montant == 'balance':
            montant = self.balance
        elif self.methode_calcul_montant == 'pc':
            pc = self.pc_prelevement
            if pc > 100:
                pc = 100
            elif pc < 0:
                pc = 0
            montant = self.total_ttc * (pc/100.)
        else:  # (methode_calcul_montant == 'fixe' normalement)
            montant = self.montant_prelevement

        if montant > self.balance:
            montant = self.balance
            self.pc_prelevement = 100
        if montant < 0:
            montant = 0
            self.pc_prelevement = 0

        self.montant_prelevement = montant
        if self.methode_calcul_montant != 'pc' and self.total_ttc != 0:
            self.pc_prelevement = 100 * (float(montant)/self.total_ttc)

    # Fonctions create et write
    # Le champ montant_prelevement est en lecture seule quand le choix du montant est un % du TTC
    # et dans ce cas, la valeur n'est pas transmise au serveur.
    # On doit recalculer ce champ pour l'enregistrer.

    @api.model
    def create(self, vals):
        if 'methode_calcul_montant' in vals and 'total_ttc' in vals and 'pc_prelevement' in vals and vals['methode_calcul_montant'] == 'pc':
            vals['montant_prelevement'] = vals['total_ttc'] * (vals['pc_prelevement']/100.)
        return super(OfPaiementEdiLine, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(OfPaiementEdiLine, self).write(vals)
        for facture in self:
            # On regarde si c'est le mode de calcul qui a été changé.
            # Si oui, on récupère le nouveau mode.
            methode_calcul_montant = facture.methode_calcul_montant

            # On recalcule le montant du prélèvement en fonction du mode de calcul.
            if methode_calcul_montant == 'pc':
                montant_prelevement = facture.total_ttc * (facture.pc_prelevement/100.)
                if montant_prelevement > facture.balance:
                    montant_prelevement = facture.balance
            elif methode_calcul_montant == 'balance':
                montant_prelevement = facture.balance
            else:
                # Si c'est montant fixe, pas besoin d'initialiser, le champ n'est pas en lecture seule et est transmis.
                continue

            if facture.montant_prelevement != montant_prelevement:
                facture.montant_prelevement = montant_prelevement
        return res
