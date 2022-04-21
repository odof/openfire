# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import time
import unicodedata
import re
import base64


class AccountPayment(models.Model):
    _inherit = "account.payment"

    service_ids = fields.Many2many('of.service', 'of_service_payment_rel', 'payment_id',
                                   'service_id', string=u"Demandes d'intervention", copy=False, readonly=True)


class OfPaiementEdi(models.Model):
    _inherit = 'of.paiement.edi'

    @api.model
    def _default_type_source(self):
        active_model = self.env.context.get('active_model', 'account.invoice')
        if active_model == 'account.invoice':
            return 'account.invoice'
        elif active_model == 'of.service':
            return 'of.service'
        return False

    @api.model
    def _default_mode_calcul(self):
        active_model = self.env.context.get('active_model', 'account.invoice')
        if active_model == 'of.service':
            return 'pc'
        return False

    @api.model
    def _default_edi_service_line_ids(self):
        """Peuple la liste des DI avec celles sélectionnées,
        en state not in ('draft', 'cancel')"""
        active_ids = self.env.context.get('active_ids', [])
        domain = [('id', 'in', active_ids), ('state', 'not in', ['draft', 'cancel'])]

        service_vals = [(5, )]  # On efface les lignes existantes

        service_ids = self.env['of.service'].search(domain)
        for service in service_ids:
            values = {
                'service_id': service.id,
                'montant_prelevement': service.price_total,
                'pc_prelevement': (service.price_total * 100.) / service.price_total if service.price_total else 0,
                'partner': service.partner_id.name,
                'total_ttc': service.price_total,
                'methode_calcul_montant': 'pc'
            }
            service_vals.append((0, 0, values))

        return service_vals

    @api.onchange('edi_service_line_ids')
    def onchange_edi_service_line_ids(self):
        # Empêcher de générer les paiements si la liste des DI a été modifiée.
        self.aff_bouton_paiement = False

    edi_service_line_ids = fields.One2many(
        'of.paiement.edi.service.line', 'edi_id', string=u"DI sélectionnées à payer",
        copy=False, default=_default_edi_service_line_ids)
    type_source = fields.Selection(
        [('account.invoice', u"Facture"), ('of.service', u"Demande d'intervention")],
        string=u"Type de source", default=_default_type_source)
    mode_calcul = fields.Selection(
        selection=[('fixe', u"Montant fixe"), ('pc', u"% du montant TTC"), ('echeance', u"Prélèvement à l'échéance")],
        default=_default_mode_calcul, string=u"Mode calcul du montant à prélever",
        required=True, help=u"Détermine comment est calculée le montant à prélever")
    montant_a_prelever = fields.Float(string=u"Montant à prélever", digits=(16, 2))
    pourcentage_a_prelever = fields.Float(string=u"% du montant à prélever", digits=(16, 2))

    @api.multi
    def action_compute_edi_service_line_ids(self):
        show_warning = False
        message = u"Les DI suivantes n'ont pas d'échéance de définie :\n\n"
        for edi_line in self.edi_service_line_ids:
            if self.mode_calcul == 'fixe':
                edi_line.methode_calcul_montant = 'fixe'
                edi_line.montant_prelevement = self.montant_a_prelever
            elif self.mode_calcul == 'pc':
                edi_line.methode_calcul_montant = 'pc'
                edi_line.pc_prelevement = self.pourcentage_a_prelever
            elif self.mode_calcul == 'echeance':
                edi_line.methode_calcul_montant = 'pc'
                if not edi_line.service_id.deadline_count:
                    show_warning = True
                    message += u"- %s\n" % edi_line.service_id.name
                    edi_line.pc_prelevement = 0.
                else:
                    edi_line.pc_prelevement = 100. / edi_line.service_id.deadline_count
            edi_line.onchange_montant_prelevement()
        for edi_line in self.edi_line_ids:
            if self.mode_calcul == 'fixe':
                edi_line.methode_calcul_montant = 'fixe'
                edi_line.montant_prelevement = self.montant_a_prelever
            elif self.mode_calcul == 'pc':
                edi_line.methode_calcul_montant = 'pc'
                edi_line.pc_prelevement = self.pourcentage_a_prelever
            elif self.mode_calcul == 'echeance':
                edi_line.methode_calcul_montant = 'pc'
                edi_line.pc_prelevement = 100
            edi_line.onchange_montant_prelevement()
        if show_warning:
            return self.env['of.popup.wizard'].popup_return(titre=u"Attention !", message=message)

    @api.multi
    def action_paiement_lcr_service(self):
        self.action_paiement_edi_service("LCR")
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def action_paiement_sepa_prev_service(self):
        self.action_paiement_edi_service("Pr. SEPA")
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def action_paiement_edi_service(self, type_paiement="Pr. SEPA"):
        """Action appelée pour effectuer un paiement EDI en fonction des DI sélectionnées"""

        self.ensure_one()

        # Teste si au moins une DI sélectionnée
        if not self.edi_service_line_ids:
            raise UserError(u"Erreur ! (#ED105)\n\nVous devez sélectionner au moins une demande d'intervention.")
        # Teste si certaines lignes ont un montant à 0
        error_lines = self.edi_service_line_ids.filtered(lambda l: not l.montant_prelevement)
        if error_lines:
            raise UserError(u"Erreur !\n\nLes DI suivantes n'ont pas de montant à prélever :\n\n- " +
                            u"\n- ".join(error_lines.mapped(lambda l: l.service_id.name)))
        # On récupère le mode de paiement et génère le fichier EDI
        if type_paiement == "LCR":
            self.genere_fichier_lcr_service(self.edi_service_line_ids)
        else:
            self.genere_fichier_sepa_prev_service(self.edi_service_line_ids)

        return True

    @api.multi
    def genere_fichier_lcr_service(self, edi_lignes):
        """Génère le fichier pour lettre de change relevé (LCR)"""
        no_ligne = 1  # No de la ligne du fichier généré
        nb_service = 0  # Nombre de DI à acquitter (pas celles montant = 0)
        chaine = ""  # Contient la chaine du fichier généré
        montant_total = 0

        # 1ère ligne : émetteur
        sortie = u"<b>Tireur :</b>\n<ul>\n<li>" + self.mode_paiement_id.company_id.name + " ["
        chaine += "0360"
        chaine += str(no_ligne).zfill(8)            # No de la ligne (no enregistrement sur 8 caractères)
        if self.mode_paiement_id.company_id.of_num_nne:  # No émetteur
            if len(self.mode_paiement_id.company_id.of_num_nne) > 6:
                raise UserError(u"Erreur ! (#ED205)\n\nLe n° national d'émetteur de l'émetteur ("
                                + self.mode_paiement_id.company_id.name + u") dépasse 6 caractères.")
            chaine += self.chaine2ascii_taille_fixe_maj(self.mode_paiement_id.company_id.of_num_nne, 6)
        else:
            chaine += " " * 6
        chaine += " " * 6                           # Type convention (6 caractères)
        if self.date_remise:                        # Date de remise (6 caractères)
            chaine += self.date_remise[8:10]+self.date_remise[5:7]+self.date_remise[2:4]
        else:
            chaine += " " * 6
        # Raison sociale de l'émetteur en majuscule sans accent et ponctuation
        # interdite tronquée ou complétée à 24 caractères
        chaine += self.chaine2ascii_taille_fixe_maj(self.mode_paiement_id.company_id.name, 24)
        if self.mode_paiement_id.bank_id.bank_id.name:  # Domiciliation (nom) bancaire du tirant
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
            raise UserError(u"Erreur ! (#ED208)\n\nVous devez choisir s'il y a une convention Dailly (LCR).\n"
                            u"Choisir \"Pas d'indication\" si pas de convention.")

        # code monnaie (euro)
        chaine += "E"

        # Référence bancaire émetteur - Configuré dans Odoo au format IBAN.
        temp = self.mode_paiement_id.bank_id.acc_number
        if temp:
            temp = temp.replace("IBAN", "").replace(" ", "").upper()
        if temp and len(temp) == 27 and temp[:2] == "FR":  # Si IBAN renseigné et français, on se base dessus.
            chaine += temp[4:9]     # Code banque
            sortie += u" Banque : " + temp[4:9]
            chaine += temp[9:14]    # Code guichet
            sortie += u" Guichet : " + temp[9:14]
            chaine += temp[14:25]   # No compte
            sortie += u" Compte : " + temp[14:25]
        else:
            # Si pas français, on ne peut pas faire de LCR car doit être un être un compte
            # au (ancien) format RIB code banque, guichet, compte, clé.
            raise UserError(u"Erreur ! (#ED210)\n\nPas de coordonnées bancaires (IBAN) françaises valides trouvées "
                            u"pour le mode de paiement " + self.mode_paiement_id.name + u".\n\n"
                            u"Pour effectuer une LCR, il faut obligatoirement des coordonnées bancaires françaises.")
        sortie += "]"
        chaine += " " * 16            # Zone réservée
        if self.date_valeur:          # Date de valeur
            chaine += self.date_valeur[8:10]+self.date_valeur[5:7]+self.date_valeur[2:4]
        else:
            chaine += " " * 6
        chaine += " " * 10  # Zone réservée

        temp = self.mode_paiement_id.company_id.company_registry  # No SIREN
        if not temp:
            chaine += " " * 15
        else:
            # On remplace les caractères accentués au cas où il y en aurait.
            temp = unicodedata.normalize('NFKD', temp).encode('ascii', 'ignore')
            if len(temp.replace(" ", "")) == 14:   # C'est un n° SIRET. Le SIREN est les 9 premiers chiffres.
                temp = temp.replace(" ", "")[:9]
            elif len(temp) > 15:
                raise UserError(u"Erreur ! (#ED215)\n\nLe n° SIREN de la société "
                                + self.mode_paiement_id.company_id.name + u" dépasse 15 caractères.")
            chaine += temp.ljust(15, " ")
            sortie += u" No SIREN : " + temp
        chaine += " " * 11  # Référence remise à faire
        chaine += "\n"
        sortie += "</li></ul>\n"

        # 2e ligne : tiré(s)
        sortie += u"<b>Tiré(s) :</b>\n<ul>\n"
        for edi_ligne in edi_lignes:

            partner_display_name = edi_ligne.service_id.partner_id.display_name
            number_or_titre = (edi_ligne.service_id.number or edi_ligne.service_id.titre)

            sortie += u"<li>"
            montant_du = edi_ligne.montant_prelevement
            # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la DI suivante
            if montant_du == 0:
                sortie += u"<b>DI non exigible</b> n° " + number_or_titre + u" de " + partner_display_name \
                          + u" [Montant total DI : " + str('%.2f' % edi_ligne.total_ttc).replace('.', ',') \
                          + u" euros]</li>\n"
                continue
            elif montant_du < 0:
                raise UserError(u"Erreur ! (#ED217)\n\nLa balance de la DI " + number_or_titre
                                + u" de " + partner_display_name
                                + u" est négative.\n\nVous ne pouvez payer par LCR que des DIs avec un solde positif.")
            else:
                nb_service = nb_service + 1

            sortie += u"DI : " + number_or_titre + u" Client : " + partner_display_name + u" ["
            rib = self._get_partner_rib(edi_ligne.service_id.partner_id)
            if not rib:
                raise UserError(u"Erreur ! (#ED220)\n\nPas de compte bancaire trouvé pour " + partner_display_name
                                + u".\n\nPour effectuer une LCR, un compte en banque "
                                  u"doit être défini pour le client de chaque DI.")
            no_ligne = no_ligne + 1
            chaine += "0660"
            chaine += str(no_ligne).zfill(8)        # No de la ligne (no enregistrement sur 8 caractères)
            chaine += " " * 8                       # Zones réservées
            chaine += " " * 10                      # Référence du tiré
            chaine += self.chaine2ascii_taille_fixe_maj(partner_display_name, 24)  # Nom du tiré (24 caractères)
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
                # Suppression de possibles caractères superflus
                temp = temp.replace("IBAN", "").replace(" ", "").upper()
            if temp and len(temp) == 27 and temp[:2] == "FR":  # Si IBAN renseigné et français, on se base dessus
                chaine += temp[4:9]     # Code banque
                sortie += " Banque : " + temp[4:9]
                chaine += temp[9:14]    # Code guichet
                sortie += " Guichet : " + temp[9:14]
                chaine += temp[14:25]   # No compte
                sortie += " Compte : " + temp[14:25]
            else:
                # Aucune référence bancaire valide
                raise UserError(u"Erreur ! (#ED225)\n\n"
                                u"Pas de coordonnées bancaires (RIB ou IBAN) valides trouvées pour "
                                + partner_display_name +
                                u".\n\n (Seuls les comptes IBAN français sont autorisés, FR suivi de 25 chiffres)")
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
            temp = edi_ligne.service_id.partner_id.company_registry\
                or edi_ligne.service_id.partner_id.commercial_partner_id.company_registry  # No SIREN
            if not temp:
                chaine += " " * 9
            else:
                # On remplace les caractères accentués au cas où il y en aurait.
                temp = unicodedata.normalize('NFKD', temp).encode('ascii', 'ignore').replace(" ", "")
                if len(temp) == 14:   # C'est un n° SIRET. Le SIREN est les 9 premiers chiffres.
                    temp = temp[:9]
                elif len(temp) > 9:
                    raise UserError(u"Erreur ! (#ED230)\n\nLe n° SIREN de " + partner_display_name
                                    + u" dépasse 9 caractères.")
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

        if nb_service:  # Si des DIs sont à payer, on génère le fichier
            sortie = u"<p>Pour enregistrer l'opération et obtenir le fichier à transmettre à la banque, " \
                     u"<b><u>vous devez valider le paiement des DIs</u></b>.</p>\n" \
                     u"<p>Le fichier lettre change relevé (LCR) a été généré avec les éléments suivants :</p>\n" \
                     + sortie
            chaine = base64.encodestring(chaine)
            self.write({
                'fichier': chaine,
                'nom_fichier': "lcr_" + time.strftime('%Y-%m-%d_%H%M%S') + ".txt",
                'type_paiement': 'LCR',
                'aff_bouton_paiement': True
            })
        else:
            sortie = u"<p>Aucune DI à payer. Le fichier n'a pas été généré.</p>\n" + sortie
            self.write({'aff_bouton_paiement': False})

        self.write({
            'date_creation': time.strftime('%Y-%m-%d %H:%M:%S'),
            'sortie': sortie
        })
        return True

    @api.multi
    def genere_fichier_sepa_prev_service(self, edi_lignes):
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
        # On classe la liste des DIs par type de prélèvement
        services_par_type = {}
        rib_rum_frst = self.env['res.partner.bank'].browse()
        for edi_ligne in edi_lignes:

            partner_display_name = edi_ligne.service_id.partner_id.display_name
            number_or_titre = (edi_ligne.service_id.number or edi_ligne.service_id.titre)

            # On récupère les coordonnées bancaires
            rib = self._get_partner_rib(edi_ligne.service_id.partner_id)
            if not rib:
                raise UserError(u"Erreur ! (#ED436)\n\nPas de compte bancaire trouvé pour le client "
                                + partner_display_name + u" (DI " + number_or_titre
                                + u").\n\nPour effectuer une opération SEPA, un compte en banque doit être défini "
                                  u"pour le client de chaque DI.")

            type_prev = rib.of_sepa_type_prev
            if not type_prev:
                raise UserError(u"Erreur ! (#ED431)\n\nLe champ \"Type de prélèvement SEPA\" "
                                u"n'a pas été configuré dans le compte en banque de " + partner_display_name
                                + u" (DI " + number_or_titre
                                + u").\n\nCe champ est obligatoire pour effectuer un prélèvement SEPA "
                                  u"et se configure dans le compte en banque de la personne débitée.")

            if type_prev not in ('FRST', 'RCUR'):
                raise UserError(u"Erreur ! (#ED432)\n\nLe champ \"Type de prélèvement SEPA\" "
                                u"contient une valeur incorrecte dans le compte en banque de " + partner_display_name
                                + u" (DI " + number_or_titre
                                + u").\n\nVeuillez configurer ce champ à nouveau. "
                                  u"Il se configure dans le compte en banque de la personne débitée.")

            if type_prev not in services_par_type:
                services_par_type[type_prev] = []
            services_par_type[type_prev].append([edi_ligne, rib])
            # On peuple la liste des mandat SEPA qui sont en "1er prélèvement"
            # qui seront à passer à la fonction de validation des paiements.
            if type_prev == 'FRST':
                rib_rum_frst |= rib

        sortie += u"<b>Tiré(s) :</b>\n<ul>\n"
        # On parcourt la liste des DIs
        # par type de prélèvement
        for type_prev in services_par_type:
            # sur chaque DI d'un type
            for edi_ligne in services_par_type[type_prev]:
                # edi_ligne est une liste de 2 éléments : 1er élément la ligne (edi_ligne[0]),
                # 2e élément le compte bancaire (edi_ligne[1]).

                montant_du = edi_ligne[0].montant_prelevement

                partner_display_name = edi_ligne[0].service_id.partner_id.display_name
                number_or_titre = (edi_ligne[0].service_id.number or edi_ligne[0].service_id.titre)

                # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul,
                # sinon passe à la DI suivante
                if montant_du == 0:
                    sortie += u"<li><b>DI non exigible</b> n° " + number_or_titre + " de " \
                              + partner_display_name + u" [Montant total facture : " \
                              + str('%.2f' % edi_ligne[0].total_ttc).replace('.', ',') + u" euros]</li>\n"
                    continue
                elif montant_du < 0:
                    raise UserError(u"Erreur ! (#ED434)\n\nLa balance de la DI "
                                    + number_or_titre + " de " + partner_display_name
                                    + u" est négative.\n\nVous ne pouvez payer par prélèvement SEPA "
                                      u"que des DIs avec un solde positif.")

                """ Info : arborescence xml générée dans cette partie
                <!-- Niveau transaction -->
                <DrctDbtTxInf> <!-- Débit à effectuer (plusieurs possible) -->
                    <PmtId>
                        <EndToEndId>...</EndToEndId> <!-- Identifiant de transaction envoyé au débiteur obligatoire -->
                    </PmtId>
                    <InstdAmt Ccy="EUR">...</InstdAmt> <!-- Montant de la transaction obligatoire -->
                    <DrctDbtTx>
                        <MndtRltdInf> <!-- Informations relatives au mandat -->
                            <MndtId>...</MndtId> <!-- Code RUM -->
                            <DtOfSgntr>...</DtOfSgntr> <!-- Date de signature du mandat -->
                            <AmdmntInd>false</AmdmntInd> <!-- facultatif Indicateur permettant de signaler une modification d'une ou plusieurs données du mandat. Valeurs : "true" (si il y a des modifications) "false" (pas de modification). Valeur par défaut : "false" -->
                        </MndtRltdInf>
                    </DrctDbtTx>
                    <DbtrAgt> <!-- Référence banque débiteur -->
                        <FinInstnId>
                            <BIC>...</BIC> <!-- Code SWIFT banque débiteur -->
                        </FinInstnId>
                    </DbtrAgt>
                    <Dbtr> <!-- Information sur le débiteur obligatoire mais balises filles facultatives-->
                        <Nm>...</Nm> <!-- Nom débiteur -->
                    </Dbtr>
                    <DbtrAcct> <!-- Informations sur le compte à débiter obligatoire -->
                        <Id>
                            <IBAN>...</IBAN>
                        </Id>
                    </DbtrAcct>
                    <RmtInf> <!-- Information sur la remise de la transaction obligatoire -->
                        <Ustrd>...</Ustrd> <!-- Libellé apparaissant sur le relevé du débiteur -->
                    </RmtInf>
                </DrctDbtTxInf>
                <!-- Fin niveau transaction -->"""

                chaine_transaction += """
                        <DrctDbtTxInf>
                            <PmtId>
                                <EndToEndId>PREV""" + time.strftime('%S%M%H%d%m%Y') + str(index) + """</EndToEndId>
                            </PmtId>
                            <InstdAmt Ccy="EUR">""" + str('%.2f' % montant_du)
                index = index + 1
                chaine_transaction += """</InstdAmt>
                            <DrctDbtTx>
                                <MndtRltdInf>
                                    <MndtId>"""
                # Référence unique de mandat (RUM). Se trouve dans le compte en banque.
                if edi_ligne[1].of_sepa_rum:
                    if edi_ligne[1].of_sepa_rum != self.chaine2ascii_taillemax(edi_ligne[1].of_sepa_rum, 35):
                        raise UserError(
                            u"Erreur ! (#ED437)\n\nLa référence unique du mandat (RUM) trouvée pour "
                            + partner_display_name + u" (DI : " + number_or_titre
                            + u") contient des caractères invalides (lettres accentuées, ...) ou dépasse 35 caractères."
                              u"\n\nLe RUM se configure dans le compte en banque de la personne débitée.")
                    chaine_transaction += str(edi_ligne[1].of_sepa_rum)
                else:
                    raise UserError(
                        u"Erreur ! (#ED438)\n\nPas de référence unique du mandat (RUM) trouvé pour "
                        + partner_display_name + u" (DI : " + number_or_titre
                        + u").\n\nLe RUM est obligatoire pour effectuer un prélèvement SEPA "
                          u"et se configure dans le compte en banque de la personne débitée.")
                chaine_transaction += """</MndtId>
                                    <DtOfSgntr>"""
                if edi_ligne[1].of_sepa_date_mandat:
                    chaine_transaction += str(edi_ligne[1].of_sepa_date_mandat)
                else:
                    raise UserError(
                        u"Erreur ! (#ED440)\n\nPas de date de signature du mandat SEPA trouvé pour "
                        + partner_display_name + u" (DI : " + number_or_titre
                        + u").\n\nCette date est obligatoire pour effectuer un prélèvement SEPA "
                          u"et se configure dans le compte en banque de la personne débitée.")
                chaine_transaction += """</DtOfSgntr>
                                    <AmdmntInd>false</AmdmntInd>
                                </MndtRltdInf>
                            </DrctDbtTx>
                            <DbtrAgt>
                                <FinInstnId>
                                    <BIC>"""
                if edi_ligne[1].bank_id.bic:
                    chaine_transaction += str(edi_ligne[1].bank_id.bic)
                else:
                    raise UserError(
                        u"Erreur ! (#ED445)\n\nPas de code BIC (SWIFT) de la banque trouvé pour "
                        + partner_display_name + u" (DI : " + number_or_titre
                        + u").\n\nIl est nécessaire de fournir ce code pour effectuer une opération SEPA.")
                chaine_transaction += """</BIC>
                                </FinInstnId>
                            </DbtrAgt>
                            <Dbtr>
                                <Nm>""" + self.chaine2ascii_taillemax(partner_display_name, 70) + """</Nm>
                            </Dbtr>
                            <DbtrAcct>
                                <Id>
                                    <IBAN>"""
                if edi_ligne[1].acc_number:
                    chaine_transaction += str(edi_ligne[1].acc_number).replace("IBAN", "").replace(" ", "").upper()
                else:
                    raise UserError(
                        u"Erreur ! (#ED450)\n\nPas d'IBAN valide trouvé pour " + partner_display_name
                        + u" (DI : " + number_or_titre
                        + u").\n\nIl est nécessaire d'avoir des coordonnées bancaires "
                          u"sous forme d'IBAN pour effectuer une opération SEPA.")
                chaine_transaction += """</IBAN>
                                </Id>
                            </DbtrAcct>"""
                if self.motif:    # On insère le motif
                    if self.motif == 'nofacture' and number_or_titre:
                        chaine_transaction += """
                            <RmtInf>
                                <Ustrd>Facture """ + self.chaine2ascii_taillemax(number_or_titre, 140) + """</Ustrd>
                            </RmtInf>"""
                chaine_transaction += """
                        </DrctDbtTxInf>"""
                nb_transaction = nb_transaction + 1
                nb_transaction_lot = nb_transaction_lot + 1
                montant_total = montant_total + montant_du
                montant_total_lot = montant_total_lot + montant_du
                sortie += u"<li>DI : " + number_or_titre + u" Client : " + partner_display_name + " ["
                if edi_ligne[1].bank_name:
                    sortie += edi_ligne[1].bank_name + " "
                sortie += u"BIC : " + edi_ligne[1].bank_bic + u" IBAN : " \
                          + str(edi_ligne[1].acc_number).upper() + u"] - <b>Montant : " \
                          + str('%.2f' % montant_du).replace('.', ',') + u" euros</b></li>\n"
                # Fin parcours chaque DI d'un type

            # Si pas de DI à payer en fonction de l'échéancier dans ce lot, on passe au lot suivant
            if nb_transaction_lot == 0:
                continue

            # On génére le lot

            """ Info : arborescence xml générée dans cette partie
            <!-- Lot de transaction -->
            <PmtInf> <!-- Instructions de prélèvements obligatoire au moins une fois-->
                <PmtInfId>...</PmtInfId> <!-- Identifiant du lot de transactions Peut être la même valeur que GrpHdr si un seul lot de transaction obligatoire -->
                <PmtMtd>DD</PmtMtd> <!-- Méthode de paiement obligatoire -->
                <NbOfTxs>...</NbOfTxs> <!-- Nb de transaction du lot facultatif -->
                <CtrlSum>...</CtrlSum> <!-- Cumul des sommes des transactions du lot facultatif -->
                <PmtTpInf> <!-- Information sur le type de paiement Normalement facultatif mais certaines banques attendent cet élément -->
                    <SvcLvl> <!-- Niveau de service -->
                        <Cd>SEPA</Cd> <!-- Contient la valeur SEPA -->
                    </SvcLvl>
                    <LclInstrm>
                        <Cd>CORE</Cd> <!-- CORE pour les débits avec une personne physique, B2B pour les débits entre entreprises -->
                    </LclInstrm>
                    <SeqTp>...</SeqTp> <!-- Type de séquence : OOFF pour un débit ponctuel, FIRST pour un 1er débit régulier, RCUR pour un débit régulier récurrent, FINAL pour un dernier débit récurrent -->
                </PmtTpInf>
                <ReqdColltnDt>...</ReqdColltnDt> <!-- Date d'échéance -->
                <Cdtr> <!-- Information sur le créancier -->
                    <Nm>...</Nm> <!-- Nom du créancier facultatif -->
                </Cdtr>
                <CdtrAcct> <!-- Information du compte du créditeur -->
                    <Id> <!-- Peut aussi contenir balise CCy pour monnaie au format ISO -->
                        <IBAN>...</IBAN>
                    </Id>
                </CdtrAcct>
                <CdtrAgt> <!-- Banque du créancier -->
                    <FinInstnId>
                        <BIC>...</BIC> <!-- Code SWIFT de la banque facultatif -->
                    </FinInstnId>
                </CdtrAgt>
                <ChrgBr>SLEV</ChrgBr> <!-- Valeur fixe SLEV -->
                <CdtrSchmeId> <!-- Identification du créancier -->
                    <Id>
                        <PrvtId>
                            <Othr>
                                <Id>...</Id> <!-- Identifiant du créancier ICS -->
                                <SchmeNm>
                                    <Prtry>SEPA</Prtry> <!-- De valeur fixe SEPA -->
                                </SchmeNm>
                            </Othr>
                        </PrvtId>
                    </Id>
                </CdtrSchmeId>
            </PmtInf>
            <!-- Fin lot de transaction -->
            """

            chaine_lot += """
                <PmtInf>
                    <PmtInfId>LOT""" + time.strftime('%S%M%H%d%m%Y') + str(index) + """</PmtInfId>
                    <PmtMtd>DD</PmtMtd>
                    <NbOfTxs>""" + str(nb_transaction_lot) + """</NbOfTxs>
                    <CtrlSum>""" + str('%.2f' % montant_total_lot) + """</CtrlSum>
                    <PmtTpInf>
                        <SvcLvl>
                            <Cd>SEPA</Cd>
                        </SvcLvl>
                        <LclInstrm>
                            <Cd>CORE</Cd>
                        </LclInstrm>
                        <SeqTp>""" + str(type_prev) + """</SeqTp>
                    </PmtTpInf>
                    <ReqdColltnDt>""" + self.date_echeance + """</ReqdColltnDt>
                    <Cdtr>
                        <Nm>""" + self.chaine2ascii_taillemax(self.mode_paiement_id.company_id.name, 70) + """</Nm>
                    </Cdtr>
                    <CdtrAcct>
                        <Id>
                            <IBAN>"""
            index = index + 1
            if self.mode_paiement_id.bank_id.acc_number:
                chaine_lot += str(self.mode_paiement_id.bank_id.acc_number).replace("IBAN", "").replace(" ", "").upper()
            else:
                raise UserError(
                    u"Erreur ! (#ED420)\n\nPas d'IBAN valide trouvé pour le mode de paiement "
                    + self.mode_paiement_id.name
                    + u".\n\nIl est nécessaire d'avoir des coordonnées bancaires sous forme d'IBAN "
                      u"pour effectuer une opération SEPA.")
            chaine_lot += """</IBAN>
                        </Id>
                    </CdtrAcct>
                    <CdtrAgt>
                        <FinInstnId>
                            <BIC>"""
            if self.mode_paiement_id.bank_id.bank_bic:
                chaine_lot += str(self.mode_paiement_id.bank_id.bank_bic)
            else:
                raise UserError(
                    u"Erreur ! (#ED425)\n\nPas de code BIC (SWIFT) de la banque attachée au mode de paiement "
                    + self.mode_paiement_id.name
                    + u".\n\nIl est nécessaire de fournir ce code pour effectuer une opération SEPA.")
            chaine_lot += """</BIC>
                        </FinInstnId>
                    </CdtrAgt>
                    <ChrgBr>SLEV</ChrgBr>
                    <CdtrSchmeId>
                        <Id>
                            <PrvtId>
                                <Othr>
                                    <Id>"""
            if self.mode_paiement_id.company_id.of_num_ics:
                chaine_lot += str(self.mode_paiement_id.company_id.of_num_ics)
            else:
                raise UserError(
                    u"Erreur ! (#ED430)\n\nPas d'identifiant créancier SEPA (ICS) trouvé pour l'émetteur ("
                    + self.mode_paiement_id.company_id.name
                    + u").\n\nCet identifiant est obligatoire pour effectuer un prélèvement SEPA "
                      u"et se configure dans configuration/société/" + self.mode_paiement_id.company_id.name + ".")
            chaine_lot += """</Id>
                                    <SchmeNm>
                                        <Prtry>SEPA</Prtry>
                                    </SchmeNm>
                                </Othr>
                            </PrvtId>
                        </Id>
                    </CdtrSchmeId>"""
            # On ajoute les transactions
            chaine_lot = chaine_lot + chaine_transaction + """
                </PmtInf>\n"""
            montant_total_lot = 0
            nb_transaction_lot = 0
            chaine_transaction = ""
            # Fin parcours par type

        # Fin parcours de toutes les DIs
        sortie += u"</ul>\n"

        # On ajoute l'en-tête.

        """ Info : arborescence xml générée dans cette partie
        <?xml version="1.0" encoding="utf-8"?>
        <Document xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">
            <CstmrDrctDbtInitn>
                <GrpHdr> <!-- En tête -->
                    <MsgId>...</MsgId> <!-- Identifiant unique du message M -->
                    <CreDtTm>...</CreDtTm>    <!-- Date de création au format ISO M -->
                    <NbOfTxs>...</NbOfTxs>    <!-- Nb total de transactions dans le fichier M -->
                    <CtrlSum>...</CtrlSum> <!-- somme totale des transactions point pour décimale -->
                    <InitgPty>    <!-- élément de type Partyidentification32 Partie initiatrice de la transaction peut contenir nom créancier adresse Obligatoire mais peut être vide -->
                        <Nm>...</Nm>
                    </InitgPty>
                </GrpHdr> <!-- Fin en-tête -->
            </CstmrDrctDbtInitn>
        </Document>
        """

        chaine_entete += """<?xml version="1.0" encoding="utf-8"?>
        <Document xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">
            <CstmrDrctDbtInitn>
                <GrpHdr>
                    <MsgId>MES""" + time.strftime('%S%M%H%d%m%Y') + str(index) + """</MsgId>
                    <CreDtTm>""" + str(self.date_creation).replace(' ', 'T') + """</CreDtTm>
                    <NbOfTxs>""" + str(nb_transaction) + """</NbOfTxs>
                    <CtrlSum>""" + str('%.2f' % montant_total) + """</CtrlSum>
                    <InitgPty>
                        <Nm>""" + self.chaine2ascii_taillemax(self.mode_paiement_id.company_id.name, 70) + """</Nm>
                    </InitgPty>
                </GrpHdr>\n"""

        # On met l'en-tête de début et les balises de fin
        chaine = chaine_entete + chaine_lot + """
            </CstmrDrctDbtInitn>
        </Document>"""

        sortie += u"<b>Montant total : " + str('%.2f' % montant_total).replace('.', ',') + " euros</b><br>\n"
        sortie = "BIC : " + str(self.mode_paiement_id.bank_id.bank_bic) + " IBAN : " \
                 + str(self.mode_paiement_id.bank_id.acc_number).upper() + "]</li>\n</ul>\n" + sortie
        if self.mode_paiement_id.bank_id.bank_name:
            sortie = self.mode_paiement_id.bank_id.bank_name + " " + sortie

        sortie = "<b>Tireur :</b>\n<ul>\n<li>" + self.mode_paiement_id.company_id.name + " [" + sortie

        if nb_transaction:  # Si des DIs sont à payer, on génère le fichier
            sortie = u"<p>Pour enregistrer l'opération et obtenir le fichier à transmettre à la banque, " \
                     u"<b><u>vous devez valider le paiement des DIs</u></b>.</p>\n" \
                     u"<p>Le fichier prélèvement SEPA a été généré avec les éléments suivants :</p>\n" + sortie

            # On remplace les 4 espaces d'indentation par une tabulation pour diminuer la taille du fichier.
            chaine = chaine.replace("    ", "\t")
            chaine = base64.encodestring(chaine)
            self.write({
                'fichier': chaine,
                'nom_fichier': u"prélèvements_sepa_" + time.strftime('%Y-%m-%d_%H%M%S') + ".txt",
                'type_paiement': 'Pr. SEPA',
                'aff_bouton_paiement': True
            })
        else:
            sortie = u"<p>Aucune DI à payer. Le fichier n'a pas été généré.</p>\n" + sortie
            self.write({'aff_bouton_paiement': False, 'fichier': ''})

        self.write({
            'date_creation': time.strftime('%Y-%m-%d %H:%M:%S'),
            'sortie': sortie
        })

        # On retourne pour la fonction de validation des paiements la liste des mandats SEPA 'FRST' à passer en 'RCUR'
        return rib_rum_frst

    @api.multi
    def action_enregistre_paiements_service(self):
        """Enregistre les paiements des DI suite à un paiement EDI"""
        sortie = ""
        if not self.aff_bouton_paiement:
            raise UserError(
                u"Erreur ! (#ED303)\n\nVous avez modifié la liste des DI depuis la dernière génération "
                u"du fichier de paiements.\n\nRegénérez une nouvelle fois le fichier "
                u"avant d'effectuer une nouvelle validation des paiements.")

        # On regénère les fichiers LCR ou SEPA au cas où il y aurait eu des modifications
        # sur les DIs/clients/émetteur depuis la génération.
        rib_rum_frst = False
        if self.type_paiement == "LCR":
            self.genere_fichier_lcr_service(self.edi_service_line_ids)
        else:
            rib_rum_frst = self.genere_fichier_sepa_prev_service(self.edi_service_line_ids)

        paiements = []

        # Pour des raisons de performance d'Odoo (cache), on récupère d'abord les données dans une liste,
        # puis on enregistre les paiements.
        for edi_ligne in self.edi_service_line_ids:

            montant_du = edi_ligne.montant_prelevement

            # On vérifie que le montant à payer en fonction de l'échéancier n'est pas nul, sinon passe à la DI suivante
            if montant_du == 0:
                continue

            paiements.append({
                'service_ids': [(6, 0, [edi_ligne.service_id.id])],
                'amount': montant_du,
                'payment_date': self.date_remise,
                'communication': '',
                'partner_id': edi_ligne.service_id.partner_id.id,
                'partner_type': 'customer' if edi_ligne.service_id.partner_id.customer else 'supplier',
                'journal_id': self.mode_paiement_id.journal_id.id,
                'payment_type': 'inbound',
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'payment_difference_handling': 'open',
                'writeoff_account_id': False,
                'of_payment_mode_id': self.mode_paiement_id.id,
            })

        payment_obj = self.env['account.payment']

        # On parcourt à nouveau les paiements pour les valider.
        for paiement in paiements:
            # On crée le paiement.
            payment = payment_obj.create(paiement)

            if not payment:
                service = self.env['account.invoice'].browse(paiement['service_ids'][0][2])
                raise UserError(
                    u"Erreur ! (#ED310)\n\nErreur création du paiement pour la DI n° "
                    + (service.number or service.titre) + u" , client : "
                    + service.partner_id.display_name + u".\n\nAucun paiement n'a été en conséquence validé.")
            payment.post()  # On le confirme.

        # Si c'est un prélèvement SEPA, on met le champ type de prélèvement SEPA
        # de chaque client à récurrent en cours si était à 1er prélèvement à venir
        if self.type_paiement == 'Pr. SEPA' and rib_rum_frst:
            rib_rum_frst.write({'of_sepa_type_prev': 'RCUR'})

        sortie = u"<p>Le paiement des DIs a été effectué.</p>\n" \
                 u"<p>Il vous reste à transmettre le fichier à votre banque.</p>\n" \
                 u"<p>-----------------------------------------------</p>\n" + sortie

        if self.sortie:   # On récupère la sortie d'avant si elle existe
            sortie = sortie + self.sortie
        self.write({
            'sortie': sortie,
            'aff_bouton_paiement': False,
            'aff_bouton_genere_fich': False
        })
        return {'type': 'ir.actions.do_nothing'}


class OfPaiementEdiServiceLine(models.Model):
    """DI à payer par EDI"""
    _name = 'of.paiement.edi.service.line'
    _description = u"Demande d'intervention à payer par EDI"

    service_id = fields.Many2one(
        'of.service', string=u"Demande d'intervention", required=True, domain="[('state','not in',['cancel']')]")
    edi_id = fields.Many2one('of.paiement.edi', 'EDI')

    partner = fields.Char(string=u'Partenaire', related='service_id.partner_id.name', readonly=True)
    currency_id = fields.Many2one(related='service_id.currency_id')
    montant_prelevement = fields.Monetary(string=u'Montant à prélever')
    total_ttc = fields.Monetary(string=u'Total TTC', related='service_id.price_total', readonly=True)

    pc_prelevement = fields.Float(string=u'% du montant TTC de la DI à prélever')
    methode_calcul_montant = fields.Selection(
        [('fixe', u'montant fixe'), ('pc', u'% du montant TTC de la DI')],
        string=u"Mode calcul du montant à prélever", required=True,
        help=u"Détermine comment est calculée le montant à prélever")

    _sql_constraints = [
        ('service_edi_uniq', 'unique (service_id, edi_id)',
         u"Erreur : une même demande d'intervention a été saisie plusieurs fois "
         u"dans la liste des demandes d'intervention à payer.")
    ]

    @api.onchange('methode_calcul_montant', 'pc_prelevement', 'montant_prelevement', 'service_id')
    def onchange_montant_prelevement(self):
        if self.methode_calcul_montant in ['pc', 'echeance']:
            pc = self.pc_prelevement
            if pc > 100:
                pc = 100
            elif pc < 0:
                pc = 0
            # On ne veut pas plus de 2 chiffres après la virgule
            montant = round(self.total_ttc * (pc/100.), 2)
        else:  # (methode_calcul_montant == 'fixe' normalement)
            montant = self.montant_prelevement

        if montant > self.total_ttc:
            montant = self.total_ttc
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
        if 'methode_calcul_montant' in vals and 'total_ttc' in vals \
                and 'pc_prelevement' in vals and vals['methode_calcul_montant'] == 'pc':
            vals['montant_prelevement'] = vals['total_ttc'] * (vals['pc_prelevement']/100.)
        return super(OfPaiementEdiServiceLine, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(OfPaiementEdiServiceLine, self).write(vals)
        for service in self:
            # On regarde si c'est le mode de calcul qui a été changé.
            # Si oui, on récupère le nouveau mode.
            methode_calcul_montant = service.methode_calcul_montant

            # On recalcule le montant du prélèvement en fonction du mode de calcul.
            if methode_calcul_montant == 'pc':
                montant_prelevement = service.total_ttc * (service.pc_prelevement/100.)
                if montant_prelevement > service.total_ttc:
                    montant_prelevement = service.total_ttc
            else:
                # Si c'est montant fixe, pas besoin d'initialiser, le champ n'est pas en lecture seule et est transmis.
                continue

            # On utilise round() pour arrondir les montants qui peuvent être calculés avec des pourcentages
            # et donc donner pleins de chiffres avec la virgule. Ce qui entraine une récursion infinie.
            if round(service.montant_prelevement, 2) != round(montant_prelevement, 2):
                service.montant_prelevement = montant_prelevement
        return res
