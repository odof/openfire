# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import time
import unicodedata
import re
import base64


class OfWizardExportWinfic(models.TransientModel):
    """Export comptable vers logiciels Fiducial (Winfic et Winsis)"""
    _name = 'of.wizard.winfic'
    _description = u"Export comptable vers logiciels Fiducial (Winfic et Winsis)"

    sortie = fields.Html('')
    fichier = fields.Binary(u'Télécharger le fichier')
    nom_fichier = fields.Char('Nom du Fichier', size=64, default="ECRITURE.WIN")

    @api.multi
    def genere_fichier_winfic(self):
        """Action appelée pour générer le fichier Winfic/Winsis"""

        self.ensure_one()
        # On récupère les factures selectionnées
        sortie = ""
        move_line_obj = self.env['account.move.line']
        liste_ecritures = move_line_obj.browse(self._context.get('active_ids', []))

        # Teste si au moins une facturé sélectionnée
        if not liste_ecritures:
            raise UserError(u"Erreur ! (#ED105)\n\nVous devez sélectionner au moins une écriture comptable.")

        no_ligne = 1  # No de la ligne du fichier généré
        chaine = ""  # Contient la chaine du fichier généré
        liste_comptes = {} # Liste des comptes comptables utilisés lors de l'export (pour générer lignes e1)
        erreur = False

        for ecriture in liste_ecritures:
            if len(ecriture.journal_id.code) != 2:
                sortie += u"Erreur écriture ligne " + str(no_ligne) + u" : le code du journal " + str(ecriture.journal_id.code) + u" ne fait pas 2 caractères.<br>\n"
                erreur = True
            chaine += ecriture.journal_id.code + '|' # Code du journal
            date_piece = ecriture.move_id.date
            chaine += date_piece[8:10] + date_piece[5:7] + date_piece[0:4] + '|' # Date de la pièce
            chaine += '     1|' # No du folio
            chaine += str(no_ligne).rjust(6) + '|' # N° de l'écriture dans le folio
            chaine += ecriture.date[8:10] + ecriture.date[5:7] + ecriture.date[2:4] + '|' # Date de l'écriture
            if len(ecriture.account_id.code) != 6: # N° compte comptable
                sortie += u"Erreur écriture ligne " + str(no_ligne) + u" : le n° du compte " + str(ecriture.account_id.code) + u" ne fait pas 6 caractères.<br>\n"
                erreur = True
            chaine += ecriture.account_id.code  + '|' # No du compte
            if not ecriture.account_id.code in liste_comptes:
                liste_comptes[ecriture.account_id.code] = ecriture.account_id.name
            chaine += str('%.2f' % ecriture.debit).replace('.', ',').rjust(13) + '|'  # Débit
            chaine += str('%.2f' % ecriture.credit).replace('.', ',').rjust(13) + '|'  # Crédit
            chaine += self.chaine2ascii_taille_fixe_maj(ecriture.name, 30) + '|' # Libellé
            chaine += '  |' # Lettrage
            #if len(ecriture.move_id.name) > 5:
            #    sortie += u"Erreur écriture ligne " + str(no_ligne) + u" : le numéro de la pièce comptable " + str(ecriture.move_id.name) + u" fait plus de 5 caractères.<br>\n"
            #    erreur = True
            chaine += str(ecriture.move_id.name[-5:]).rjust(5) + '|' # N° de la pièce
            chaine += " " * 4 + '|' # Code statistique
            if ecriture.date_maturity: # Date d'échéance
                chaine += ecriture.date_maturity[8:10] + ecriture.date_maturity[5:7] + ecriture.date_maturity[0:4] + '|'
            else:
                chaine += " " * 8
            chaine += '1|' # Monnaie (euro)
            chaine += ' | |          0|  |' # Filler + Ind. compteur + Quantité + Filler
            chaine += "\r\n"
            no_ligne = no_ligne + 1

        # On crée les lignes "1e" (libellé des comptes)
        no_ligne = 1
        date = time.strftime('%d%m%Y')
        for compte in liste_comptes:
            chaine += '1e|' + date + '|     1|' + str(no_ligne).rjust(8) + '|     1|'
            chaine += compte
            chaine += '|         0,00|         0,00|' + self.chaine2ascii_taille_fixe_maj(liste_comptes[compte], 30)
            chaine += '|  |     |    |        |1| | |          0|  |'
            chaine += "\r\n"
            no_ligne = no_ligne + 1

        if erreur:
            sortie = u"<p>Il y a eu des erreurs. Le fichier d'export ne peut être généré.</p>\n" + sortie
            self.write({'fichier': ''})
        else:
            if chaine:  # On génère le fichier.
                sortie = u"<p>Le fichier d'export a été généré. Vous pouvez l'enregistrer.</p>\n" + sortie
                chaine = base64.encodestring(chaine)
                self.write({
                    'fichier': chaine,
                    'nom_fichier': "ECRITURE.WIN",
                })
            else:
                sortie = u"<p>Le fichier est vide.</p>\n" + sortie

        self.write({
            'sortie': sortie
        })
        return {"type": "ir.actions.do_nothing"}

    def chaine2ascii_taille_fixe_maj(self, chaine, longueur):
        """Retourne la chaine en majuscule sans accent et ponctuation autre que ().,/+-:*espace et tronquée ou complétée à (longueur) caractères"""
        if not chaine or not longueur or longueur < 1:
            return False
        chaine = unicodedata.normalize('NFKD', chaine).encode('ascii', 'ignore')
        chaine = re.sub(r'[^0-9A-Za-z\(\)\ \.\,\/\+\-\:\*]', ' ', chaine)
        chaine = chaine[:longueur]
        return chaine.upper().ljust(longueur)

    def chaine2ascii_taillemax(self, chaine, longueur):
        """Retourne la chaine sans accent et ponctuation autre que /-?:().,‟espace et tronquée à (longueur) caractères"""
        if not chaine or not longueur or longueur < 1:
            return False
        chaine = unicodedata.normalize('NFKD', chaine).encode('ascii', 'ignore')
        chaine = re.sub(r'[^0-9A-Za-z\(\)\ \.\,\/\?\-\:]', ' ', chaine)
        return chaine[:longueur]
