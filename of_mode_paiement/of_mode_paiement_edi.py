# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import UserError
from openerp import netsvc
import time
import unicodedata
import re
import base64


class of_account_payment_mode(models.Model):
    "Ajouter compte en banque aux modes de paiement"
    _inherit = "of.account.payment.mode"

    bank_id = fields.Many2one('res.partner.bank', "Compte bancaire", help='Compte bancaire pour le mode de paiement.')


class of_paiement_edi(models.Model):
    "Paiement par échange de fichier informatique"
    _name = 'of.paiement.edi'
    _description = "Effectuer un paiement par echange de fichier informatique"
    
    name = fields.Char("Nom", size=64, required=False)
    type_paiement = fields.Char('type de paiement par EDI', size=16, required=True)
    date_creation = fields.Date('Date de création fichier EDI', required=True)
    date_remise = fields.Date('Date de remise fichier EDI', required=False)
    date_echeance = fields.Date('Date d\'échéance paiement EDI', required=False)
    date_valeur = fields.Date('Date de valeur paiement EDI', required=False)
    fichier_edi = fields.Text('Fichier EDI')


class res_company(models.Model):
    _inherit = "res.company"
    
    of_num_nne = fields.Char("Numéro national d'émetteur (NNE)", size=6, required=False, help=u"Numéro national d'émetteur pour opérations bancaires par échange de fichiers informatiques")
    of_num_ics = fields.Char("Identifiant créancier SEPA (ICS)", size=32, required=False, help=u"Identifiant créancier SEPA (ICS) pour opérations bancaires SEPA par échange de fichiers informatiques")
    

class res_partner(models.Model):
    _inherit = "res.partner"
    
    of_sepa_rum = fields.Char("Référence unique du mandat (RUM) SEPA", size=35, required=False, help=u"Référence unique du mandat (RUM) SEPA pour opérations bancaires par échange de fichiers informatiques")
    of_sepa_date_mandat = fields.Date("Date de signature du mandat SEPA", required=False, help=u"Date de signature du mandat SEPA pour opérations bancaires par échange de fichiers informatiques")
    of_sepa_type_prev = fields.Selection([("FRST","1er prélèvement récurrent à venir"),("RCUR","Prélèvement récurrent en cours")], 'Type de prélèvement (SEPA)', required=True, default='FRST', help=u"Type de prélèvement SEPA.\n- Mettre à 1er prélèvement quand aucun prélèvement n'a été effectué avec ce mandat.\nLors d'un 1er prélèvement, cette option passera automatiquement à prélèvement récurrent en cours.\n\n- Mettre à prélèvement récurrent en cours lorsqu'un prélèvement a déjà été effectué avec ce mandat.\n\n")
    company_registry = fields.Char(u'Registre de la société', size=64) # Migration : on ajoute le champ company_registry pour les partenaires. Il est définit dans of_sales mais on le rajoute au cas où of_sales ne serait pas installé.
    
#     _defaults = {
#         'of_sepa_type_prev': 'FRST'
#     }

class wizard_paiement_edi(models.TransientModel):
    """Ce wizard va effectuer un paiement par échange de fichier informatique"""
    _name = 'wizard.paiement.edi'
    _description = u"Effectuer un paiement par echange de fichier informatique"

    date_remise = fields.Date(u'Date de remise du paiement', required=True, default=fields.Datetime.now)
    date_valeur = fields.Date(u'Date de valeur du paiement (LCR)', required=False, default=fields.Datetime.now)
    date_echeance = fields.Date(u"Date d'échéance du paiement", required=True, default=fields.Datetime.now)
    # À activer quand migration échéancier effectué : type_montant_facture = fields.Selection([('solde','solde de la facture'),('echeancier',"en fonction de l'échéancier")], u'Montant à payer des factures', required=True, help=u"Détermine comment est calculé le montant à payer des factures")
    type_montant_facture = fields.Selection([('solde','solde de la facture')], u'Montant à payer des factures', required=True, help=u"Détermine comment est calculé le montant à payer des factures")
    motif = fields.Selection([('nofacture','No de facture')], 'Motif opération (SEPA)', required=False, help=u"Texte qui apparaît sur le relevé bancaire du débiteur", default='nofacture')
    date_creation = fields.Text('Date de création', default=fields.Datetime.now)
    mode_paiement_id = fields.Many2one('of.account.payment.mode', 'Mode de paiement', required=True)
    journal_id = fields.Many2one(related='mode_paiement_id.journal_id', string='Journal', store=False)
    sortie = fields.Text('')
    fichier = fields.Binary(u'Télécharger le fichier')
    nom_fichier = fields.Char('Nom du Fichier', size=64, default="edi_" + str(fields.Datetime.now) + ".txt")
    aff_bouton_paiement = fields.Boolean(default=False)
    aff_bouton_genere_fich = fields.Boolean(default=True)
    type_paiement = fields.Char('Type de paiement', size=16)

#     _defaults = {
#         'date_remise': time.strftime('%Y-%m-%d'),
#         'date_valeur': time.strftime('%Y-%m-%d'),
#         'date_echeance': time.strftime('%Y-%m-%d'),
#         'date_creation': time.strftime('%Y-%m-%d %H:%M:%S'),
#         'nom_fichier': "edi_" + time.strftime('%Y-%m-%d') +".txt",
#         'motif': 'nofacture',
#         'aff_bouton_paiement': False,
#         'aff_bouton_genere_fich': True
#     }
   
    @api.multi
    def action_paiement_sepa_prev(self):
        self.action_paiement_edi("sepa_prev")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.paiement.edi',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }

    @api.multi
    def action_paiement_lcr(self):
        self.action_paiement_edi("lcr")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.paiement.edi',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self._context
        }

    @api.multi
    def action_paiement_edi(self, type_paiement="sepa_prev"):
        """Action appelée pour effectuer un paiement EDI en fonction des factures sélectionnées"""

        self.ensure_one()
        # On récupère les factures selectionnées
        invoice_obj = self.env['account.invoice']
        liste_factures = invoice_obj.browse(self._context.get('active_ids', []))
        
        # Teste si au moins une facturé sélectionnée
        if not liste_factures:
            raise UserError(u"Erreur ! (#ED105)\n\nVous devez sélectionner au moins une facture.")
             
        # On vérifie qu'il s'agit bien de factures ouvertes non payées 
        for facture in liste_factures:
            if facture.type != "out_invoice" and facture.type != "in_refund":
                raise UserError(u"Erreur ! (#ED110)\n\nVous avez sélectionné au moins une facture qui n'est pas une facture client ou un avoir fournisseur.\n\nVous ne pouvez demander le règlement par LCR ou prélèvement SEPA que pour une facture client ou un avoir fournisseur.")
            if facture.state != "open" or facture.residual <= 0 or facture.amount_total <= 0:
                raise UserError(u"Erreur ! (#ED115)\n\nVous avez sélectionné au moins une facture non ouverte, déjà payée ou avec une balance ou un montant total négatif.\nVous ne devez sélectionner que des factures ouvertes, non payées avec une balance et un montant total positif.")
        
        # On récupère le mode de paiement du wizard et génère le fichier EDI
        if type_paiement == "lcr":
            self.genere_fichier_lcr(liste_factures)
        else:
            self.genere_fichier_sepa_prev(liste_factures)
        
        return True

    @api.multi
    def genere_fichier_lcr(self, liste_factures):
        """Génère le fichier pour lettre de change relevé (LCR)"""
        sortie = ""
        no_ligne = 1 # No de la ligne du fichier  généré
        nb_facture = 0 # Nombre de facture à acquitter (pas celles montant = 0)
        chaine = ""  # Contient la chaine du fichier généré
        montant_total = 0
        self.write({'date_creation': time.strftime('%Y-%m-%d %H:%M:%S')})
               
        # 1ère ligne : émetteur
        sortie += u"Tireur : " + self.mode_paiement_id.company_id.name + " ["
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
        chaine += "30E"                             # Code entrée, code Daily, code monnaie (euro)
        
        # référence bancaire émetteur - Configuré dans Odoo soit en IBAN
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
        chaine += " " * 10 # Zone réservée
        
        temp = liste_factures[0].company_id.company_registry    # No SIREN
        if not temp:   
            chaine += " " * 15
        else:
            if len(temp.replace(" ", "")) == 14:   # C'est un n° SIRET. Le SIREN est les 9 premiers chiffres.
                temp = temp.replace(" ", "")[0:9]
            elif len(temp) > 15:
                raise UserError(u"Erreur ! (#ED215)\n\nLe n° SIREN de la société " + liste_factures[0].company_id.name + u" dépasse 15 caractères.")
            chaine += temp.ljust(15, " ")
            sortie += u" [No SIREN : " + temp + "]"
        chaine += " " * 11 # Référence remise à faire
        chaine += "\n"
        sortie += "\n"
        
        # 2e ligne : tiré(s)
        rib_obj = self.env['res.partner.bank']
        for facture in liste_factures:
            if self.type_montant_facture == "echeancier":
                montant_du = self.montantapayer_echeancier(facture)
            else:
                montant_du = facture.residual
            
            # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la facture suivante
            if montant_du == 0:
                sortie += u"Facture non exigible suivant échéancier : " + facture.partner_id.name + u" [Rien à payer suivant échéancier] [Montant total facture : " + str('%.2f' % facture.amount_total).replace('.', ',') + u" euros]\n"
                continue
            elif montant_du < 0:
                raise UserError(u"Erreur ! (#ED217)\n\nLa balance de la facture de " + facture.partner_id.name + u" est négative.\n\nVous ne pouvez payer par LCR que des factures avec un solde positif.")
            else:
                nb_facture = nb_facture + 1
            
            sortie += u"Tiré : " + facture.partner_id.name + " ["
            rib = rib_obj.search([('partner_id', '=' , facture.partner_id.id)]) 
            if not rib:
                raise UserError(u"Erreur ! (#ED220)\n\nPas de compte bancaire trouvé pour " + facture.partner_id.name + u".\n\nPour effectuer une LCR, un compte en banque doit être défini pour le client de chaque facture.")
            no_ligne = no_ligne + 1
            chaine += "0660"
            chaine += str(no_ligne).zfill(8)        # No de la ligne (no enregistrement sur 8 caractères)
            chaine += " " * 8                       # Zones réservées
            chaine += " " * 10                      # Référence du tiré
            chaine += self.chaine2ascii_taille_fixe_maj(facture.partner_id.name, 24) # Nom du tiré (24 caractères)
            if rib[0].bank_name:                    # Domiciliation (nom) bancaire du tiré
                chaine += self.chaine2ascii_taille_fixe_maj(rib[0].bank_name, 24)
                sortie += rib[0].bank_name
            else:
                chaine += " " * 24
            chaine += "0"                           # Acceptation
            chaine += " " * 2                       # Zone réservée
            
            # référence bancaire - Configuré dans Odoo soit en IBAN
            temp = rib[0].acc_number
            if temp:
                temp = temp.replace("IBAN", "").replace(" ", "").upper() # Suppression de possibles caractères superflus
            if temp and len(temp) == 27 and temp[0:2] == "FR":  # Si IBAN renseigné et français, on se base dessus                
                chaine += temp[4:9]     # Code banque
                sortie += " Banque : " + temp[4:9]
                chaine += temp[9:14]    # Code guichet
                sortie += " Guichet : " + temp[9:14]
                chaine += temp[14:25]   # No compte
                sortie += " Compte : " + temp[14:25]
            elif rib[0].bank_code and len(rib[0].bank_code) == 5 and rib[0].office and len(rib[0].office) == 5 and rib[0].rib_acc_number and len(rib[0].rib_acc_number) == 11 and rib[0].key and len(rib[0].key) == 2:   # On prend le RIB sinon si renseigné
                chaine += rib[0].bank_code
                chaine += rib[0].office
                chaine += rib[0].rib_acc_number
                sortie += " Banque : " + rib[0].bank_code + " Guichet : " + rib[0].office + " Compte : " + rib[0].rib_acc_number
            else:   # Aucune référence bancaire valide
                raise UserError(u"Erreur ! (#ED-225)\n\nPas de coordonnées bancaires (RIB ou IBAN) valides trouvées pour " + facture.partner_id.name + u".\n\n (codes banque et guichet 5 chiffres, n° compte 11 chiffres et clé 2 chiffres)")
            sortie += "]"
            montant_total = montant_total + montant_du
            sortie += " [Montant : " + str('%.2f' % montant_du).replace('.', ',') + " euros]"
            chaine += str('%.2f' % montant_du).replace('.', '').zfill(12) # Montant
            chaine += " " * 4                       # Zone réservée
            chaine += self.date_echeance[8:10]+self.date_echeance[5:7]+self.date_echeance[2:4]    # Date d'échéance
            chaine += self.date_creation[8:10]+self.date_creation[5:7]+self.date_creation[2:4]    # Date de création
            chaine += " " * 4                       # Zone réservée
            chaine += " "                           # Type
            chaine += " " * 3                       # Nature
            chaine += " " * 3                       # Pays
            temp = facture.partner_id.company_registry    # No SIREN
            if not temp:
                chaine += " " * 9
            else:
                if len(temp.replace(" ", "")) == 14:   # C'est un n° SIRET. Le SIREN est les 9 premiers chiffres.
                    temp = temp.replace(" ", "")[0:9]
                elif len(temp) > 9:
                    raise UserError(u"Erreur ! (#ED230)\n\nLe n° SIREN de " + facture.partner_id.name + u" dépasse 9 caractères.")
                chaine += temp.ljust(9, " ")
                sortie += " [No SIREN : " + temp + "]"
            chaine += " " * 10                       # Référence tireur
            chaine += "\n"
            sortie += "\n"
        
        # Dernière ligne : total
        no_ligne = no_ligne + 1
        chaine += "0860"
        chaine += str(no_ligne).zfill(8)            # No de la ligne (no enregistrement sur 8 caractères)
        chaine += " " * 90                          # Zones réservées
        sortie += u">> Montant total : " + str('%.2f' % montant_total).replace('.', ',') + " euros"
        chaine += str('%.2f' % montant_total).replace('.', '').zfill(12) # Montant total
        chaine += " " * 46                          # Zones réservées
        chaine += "\n"
        
        if nb_facture: # Si des factures sont à payer, on génère le fichier
            sortie = u"Pour enregistrer l'opération, vous devez valider le paiement des factures.\n\nLe fichier lettre change relevé (LCR) a été généré avec les éléments suivants :\n\n" + sortie
            chaine = base64.encodestring(chaine)
            self.write({'fichier': chaine})
            self.write({'nom_fichier': "lcr_" + time.strftime('%Y-%m-%d') +".txt"})
            self.write({'type_paiement': 'lcr'})
            self.write({'aff_bouton_paiement': True})
        else:
            sortie = u"Aucune facture à payer. Le fichier n'a pas été généré.\n\n" + sortie
            self.write({'aff_bouton_paiement': False})
        
        self.write({'sortie': sortie})
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
        index = 1 # Pour générer des identifiants uniques
        
        self.write({'date_creation': time.strftime('%Y-%m-%d %H:%M:%S')})
        
        rib_obj = self.env['res.partner.bank']
       
        # On doit faire un lot par type de prélèvement (frst, rcur, ...)
        # On classe la liste des factures par type de prélèvement
        factures_par_type = {}
        for facture in liste_factures:
            if not facture.partner_id.of_sepa_type_prev:
                raise UserError(u"Erreur ! (#ED431)\n\nLe champ \"Type de prélèvement SEPA\" n'a pas été configuré pour " + facture.partner_id.name + u".\n\nCe champ est obligatoire pour effectuer un prélèvement SEPA et se configure dans l'onglet Achats-Ventes du client.")
            if facture.partner_id.of_sepa_type_prev not in ('FRST','RCUR'):
                raise UserError(u"Erreur ! (#ED432)\n\nLe champ \"Type de prélèvement SEPA\" contient une valeur incorrecte pour " + facture.partner_id.name + u".\n\nVeuillez configurer ce champ à nouveau. Il se configure dans l'onglet Achats-Ventes du client.")
            if facture.partner_id.of_sepa_type_prev not in factures_par_type:
                factures_par_type[facture.partner_id.of_sepa_type_prev] = []
            factures_par_type[facture.partner_id.of_sepa_type_prev].append(facture)
        
        # On parcourt la liste des factures
        # par type de prélèvement
        for type_prev in factures_par_type:
            # sur chaque facture d'un type
            for facture in factures_par_type[type_prev]:
                if self.type_montant_facture == "echeancier":
                    montant_du = self.montantapayer_echeancier(facture)
                else:
                    montant_du = facture.residual
                
                # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la facture suivante 
                if montant_du == 0:
                    sortie += u"Facture non exigible suivant échéancier : " + facture.partner_id.name + u" [Rien à payer suivant échéancier] [Montant total facture : " + str('%.2f' % facture.amount_total).replace('.', ',') + u" euros]\n"
                    continue
                elif montant_du < 0:
                    raise UserError(u"Erreur ! (#ED434)\n\nLa balance de la facture de " + facture.partner_id.name + u" est négative.\n\nVous ne pouvez payer par prélèvement SEPA que des factures avec un solde positif.")

                # On récupère les coordonnées bancaires
                rib = rib_obj.search([('partner_id', '=' , facture.partner_id.id)])
                if not rib:
                    raise UserError(u"Erreur ! (#ED436)\n\nPas de compte bancaire trouvé pour " + facture.partner_id.name + u".\n\nPour effectuer une opération SEPA, un compte en banque doit être défini pour le client de chaque facture.")
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
                if facture.partner_id.of_sepa_rum:
                    chaine_transaction += str(facture.partner_id.of_sepa_rum)
                else:
                    raise UserError(u"Erreur ! (#ED438)\n\nPas de référence unique du mandat (RUM) trouvé pour " + facture.partner_id.name + u".\n\nLe RUM est obligatoire pour effectuer un prélèvement SEPA et se configure dans l'onglet Achats-Ventes du client.")
                chaine_transaction += """</MndtId> <!-- Code RUM -->
                                    <DtOfSgntr>"""
                if facture.partner_id.of_sepa_date_mandat:
                    chaine_transaction += str(facture.partner_id.of_sepa_date_mandat)
                else:
                    raise UserError(u"Erreur ! (#ED440)\n\nPas de date de signature du mandat SEPA trouvé pour " + facture.partner_id.name + u".\n\nCette date est obligatoire pour effectuer un prélèvement SEPA et se configure dans l'onglet Achats-Ventes du client.")
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
                    raise UserError(u"Erreur ! (#ED445)\n\nPas de code BIC (SWIFT) de la banque trouvé pour " + facture.partner_id.name + u".\n\nIl est nécessaire de fournir ce code pour effectuer une opération SEPA.")
                chaine_transaction += """</BIC> <!-- Code SWIFT banque débiteur -->
                                </FinInstnId>
                            </DbtrAgt>
                            <Dbtr> <!-- Information sur le débiteur obligatoire mais balises filles facultatives-->
                                <Nm>""" + self.chaine2ascii_taillemax(facture.partner_id.name, 70) + """</Nm> <!-- Nom débiteur -->
                            </Dbtr>
                            <DbtrAcct> <!-- Informations sur le compte à débiter obligatoire -->
                                <Id>
                                    <IBAN>"""
                if rib[0].acc_number:
                    chaine_transaction += str(rib[0].acc_number).replace("IBAN", "").replace(" ", "").upper()
                else:
                    raise UserError(u"Erreur ! (#ED450)\n\nPas d'IBAN valide trouvé pour " +  facture.partner_id.name + u".\n\nIl est nécessaire d'avoir des coordonnées bancaires sous forme d'IBAN pour effectuer une opération SEPA.")
                chaine_transaction += """</IBAN>
                                </Id>
                            </DbtrAcct>"""
                if self.motif:    # On insère le motif
                    if self.motif == 'nofacture' and facture.number:
                        chaine_transaction += """
                            <RmtInf> <!-- Information sur la remise de la transaction obligatoire -->
                                <Ustrd>Facture """ + self.chaine2ascii_taillemax(facture.number, 140) + """</Ustrd> <!-- Libellé apparaissant sur le relevé du débiteur -->
                            </RmtInf>"""
                chaine_transaction += """
                        </DrctDbtTxInf>
                        <!-- Fin niveau transaction -->"""
                nb_transaction = nb_transaction + 1
                nb_transaction_lot = nb_transaction_lot + 1
                montant_total = montant_total + montant_du
                montant_total_lot = montant_total_lot + montant_du
                sortie += u"Tiré : " + facture.partner_id.name + " ["
                if rib[0].bank_name:
                    sortie += rib[0].bank_name + " "
                sortie += "BIC : " + rib[0].bank_bic + " IBAN : " + str(rib[0].acc_number).upper() + "] [Montant : " + str('%.2f' % montant_du).replace('.', ',') + " euros]\n"
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
        
        # Fin parcourt de toutes les factures 
        # On ajoute l'en-tête
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
        
        sortie += u">> Montant total : " + str('%.2f' % montant_total).replace('.', ',') + " euros"
        sortie = "BIC : " + str(self.mode_paiement_id.bank_id.bank_bic) + " IBAN : "+ str(self.mode_paiement_id.bank_id.acc_number).upper() + "]\n" + sortie
        if self.mode_paiement_id.bank_id.bank_name:
            sortie = self.mode_paiement_id.bank_id.bank_name + " " + sortie
        
        sortie = "Tireur : " + self.mode_paiement_id.company_id.name + " [" + sortie
         
        if nb_transaction: # Si des factures sont à payer, on génère le fichier
            sortie = u"Pour enregistrer l'opération, vous devez valider le paiement des factures.\n\nLe fichier prélèvement SEPA a été généré avec les éléments suivants :\n\n" + sortie 
            chaine = base64.encodestring(chaine)
            self.write({'fichier': chaine})
            self.write({'nom_fichier': "prelevement_sepa_" + time.strftime('%Y-%m-%d') +".txt"})
            self.write({'type_paiement': 'prev_sepa'})
            self.write({'aff_bouton_paiement': True})
        else:
            sortie = u"Aucune facture à payer. Le fichier n'a pas été généré.\n\n" + sortie
            self.write({'aff_bouton_paiement': False})
            self.write({'fichier': ''})
        
        self.write({'sortie': sortie})
        
        return True

    
    @api.model
    def montantapayer_echeancier(self, facture):
        """calcul le montant à payer en fonction de l'échéancier de la facture"""
        result = 0
        date_aujourdhui = self.date_creation[0:10]
        
        if facture.residual: # montant acquitté = montant déjà payé d'après balance (total facture moins ce qui reste à payer)
            montant_acquitte = facture.amount_total - facture.residual
        else:
            montant_acquitte = 0
                
        # Si pas de ligne dans l'échéancier, on considère que la facture est à payer au comptant (échéance = date facture)
        if not facture.acompte_line_ids:
            if facture.date_invoice and date_aujourdhui >= facture.date_invoice: # Si date de facture existe et est avant la date d'échéance on doit payer le montant total
                if facture.residual:
                    result = facture.residual
                else:
                    result = facture.amount_total
            else: # La date de la facture est après aujourd'hui, rien à payer
                result = 0
        else:
            cumul_montant_echeance = 0
            # On parcourt les lignes de l'échéancier jusqu'à la date de l'exécution de l'ordre pour déterminer le montant cumulé des échéances à ce jour.
            for echeance in facture.acompte_line_ids:
                if self.date_echeance < echeance.date:
                    break
                cumul_montant_echeance = cumul_montant_echeance + echeance.montant
            
            result = cumul_montant_echeance - montant_acquitte
        
        if result < 0:
                result = 0
        return result
    
    @api.multi
    def action_enregistre_paiements(self):
        """Enregistre les paiements des factures suite à un paiement EDI"""
        sortie = ""
        if not self._context:
            raise UserError(u"Erreur ! (#ED303)\n\nLe serveur a été arrêté depuis que vous avez généré le fichier.\n\nAppuyer une nouvelle fois sur le bouton générer le fichier avant d'effectuer une nouvelle validation des paiements.")
        
        partner_obj = self.env['res.partner']
        
        # On récupère les factures selectionnées
        invoice_obj = self.env['account.invoice']
        liste_factures = invoice_obj.browse(self._context.get('active_ids', []))
        
        # On vérifie qu'il s'agit bien de factures ouvertes non payées 
        for facture in liste_factures:
            
            if self.type_montant_facture == "echeancier":
                montant_du = self.montantapayer_echeancier(facture)
            else:
                montant_du = facture.residual
            
            # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la facture suivante 
            if montant_du == 0:
                continue

            # On crée le paiement.
            payment = self.env['account.payment'].create({
                'invoice_ids': [(6, 0, [facture.id])],
                'amount': montant_du,
                'payment_date': self.date_remise,
                'communication': '',
                'partner_id': facture.partner_id.id,
                'partner_type': facture.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
                'journal_id': self.mode_paiement_id.journal_id.id,
                'payment_type': 'inbound',
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'payment_difference_handling': 'open',
                'writeoff_account_id': False,
                'of_payment_mode_id': self.mode_paiement_id.id,
            })
            
            if not payment:
                raise UserError(u"Erreur ! (#ED310)\n\nErreur création du paiement pour la facture du " + facture.date_invoice + u", client : " + facture.partner_id.name + u", montant restant à payer : " + str('%.2f' % montant_du).replace('.', ',') + u" euros.\n\nAucun paiement n'a été en conséquence validé.")
            payment.post() # On le confirme.
            
            # On met le champ type de prélèvement SEPA de chaque client à récurent en cours si était à 1er prélèvement à venir
            if facture.partner_id.of_sepa_type_prev == "FRST":
                if not facture.partner_id.write({'of_sepa_type_prev': 'RCUR'}):
                    raise UserError(u"Erreur ! (#ED320)\n\nErreur dans l'enregistrement du type de prélèvement SEPA pour : " + facture.partner_id.name + u".\n\nAucun paiement n'a été en conséquence validé.")
                
        sortie = u"Le paiement des factures a été effectué.\nIl vous reste à transmettre le fichier à votre banque.\n\n-----------------------------------------------\n\n" + sortie
        temp = {'type_paiement': self.type_paiement,
                'date_creation': self.date_creation,
                'date_remise': self.date_remise,
                'date_echeance': self.date_echeance,
                'fichier_edi': base64.decodestring(self.fichier)
                }
        # On ajoute la date de valeur si renseignée dans le formulaire
        if self.date_valeur:
            temp['date_valeur'] = self.date_valeur
        
        # On enregistre les caractéristiques du paiement EDI (date, fichier généré, ...) objet of.paiement.edi 
        if not self.env['of.paiement.edi'].create(temp):
            raise UserError(u"Erreur ! (#ED325)\n\nErreur lors de l'enregistrement du paiement pour la facture du " + facture.date_invoice + u", client : " + facture.partner_id.name + u", montant à payer : " + str('%.2f' % montant_du).replace('.', ',') + u" euros.\n\nAucun paiement n'a été en conséquence validé.")
        if self.sortie:   # On récupère la sortie d'avant si elle existe
            sortie = sortie + self.sortie
        self.write({'sortie': sortie})
        self.write({'aff_bouton_paiement': False})
        self.write({'aff_bouton_genere_fich': False})
        return True
    
    def chaine2ascii_taille_fixe_maj(self, chaine, longueur):
        """ (pour LCR) Retourne une chaine en majuscule sans accent et ponctuation autre que ().,/+-:*espace et tronquée ou complétée à (longueur) caractères"""
        if not chaine or not longueur or longueur < 1:
            return False
        chaine = unicodedata.normalize('NFKD', chaine).encode('ascii','ignore')
        #chaine = chaine.replace("'", " ")   # apostrophe par espace
        chaine = re.sub(r'[^0-9A-Za-z\(\)\ \.\,\/\+\-\:\*]', ' ', chaine)
        chaine = chaine[:longueur]
        return chaine.upper().ljust(longueur)

    def chaine2ascii_taillemax(self, chaine, longueur):
        """ (pour SEPA) Retourne une chaine sans accent et ponctuation autre que /-?:().,‟espace et tronquée à (longueur) caractères"""
        if not chaine or not longueur or longueur < 1:
            return False
        chaine = unicodedata.normalize('NFKD', chaine).encode('ascii','ignore')
        chaine = re.sub(r'[^0-9A-Za-z\(\)\ \.\,\/\?\-\:]', ' ', chaine)
        return chaine[:longueur]
