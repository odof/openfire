# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


_logger = logging.getLogger(__name__)


class OFCompanyDeletionWizard(models.TransientModel):
    _name = 'of.company.deletion.wizard'
    _description = u"Outil de suppression de société avec les objets liés"

    company_ids = fields.Many2many(comodel_name='res.company', string=u"Société à supprimer")

    @api.multi
    def action_unlink(self):
        """
        Supprime les sociétés renseignées dans le champ 'company_ids' ainsi que l'ensemble de leurs objets liés.
        :return:
        """

        # Fonction de suppression réservée à l'administrateur
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur peut effectuer cette action !")

        _logger.info(u"Company Deletion - START")

        company_ids = self.company_ids.ids
        _logger.info(u"Company Deletion - Companies %s - START" % company_ids)

        # Opportunités
        _logger.info(u"Company Deletion - Companies %s - Leads - START" % company_ids)
        self.env['crm.lead'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Leads - END" % company_ids)

        self.env.cr.commit()

        # Commandes de vente
        _logger.info(u"Company Deletion - Companies %s - Sale Orders - START" % company_ids)
        # Seules les commandes brouillon ou annulées peuvent être supprimées
        self.env['sale.order'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids),
             ('state', 'not in', ['draft', 'cancel'])]).write({'state': 'cancel'})
        self.env['sale.order'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Sale Orders - END" % company_ids)

        self.env.cr.commit()

        # Factures client
        _logger.info(u"Company Deletion - Companies %s - Customer Invoices - START" % company_ids)
        account_invoices = self.env['account.invoice'].with_context(active_test=False).search(
            [('type', 'in', ['out_invoice', 'out_refund']),
             ('company_id', 'in', self.company_ids.ids)])
        # Suppression des paiements edi
        if 'of.paiement.edi.line' in self.env:
            edi_payment_lines = self.env['of.paiement.edi.line'].with_context(active_test=False).search(
                [('invoice_id', 'in', account_invoices.ids)])
            edi_payments = edi_payment_lines.mapped('edi_id')
            edi_payment_lines.unlink()
            edi_payments.unlink()
        # Seules les factures brouillon ou annulées qui n'ont pas de numéro attribué peuvent être supprimées
        account_invoices.write({'state': 'cancel', 'move_name': False})
        account_invoices.unlink()
        _logger.info(u"Company Deletion - Companies %s - Customer Invoices - END" % company_ids)

        self.env.cr.commit()

        # Paiements client
        _logger.info(u"Company Deletion - Companies %s - Customer Payments - START" % company_ids)
        # Suppression des historiques de paiement
        if 'of.log.paiement' in self.env:
            self._cr.execute("""DELETE FROM of_log_paiement
                                WHERE       paiement_id     IN (    SELECT  id
                                                                    FROM    account_payment
                                                                    WHERE   company_id      IN %s
                                                                    AND     payment_type    = 'inbound'
                                                                );
                             """, (tuple(self.company_ids.ids), ))
        self._cr.execute("""DELETE FROM account_payment
                            WHERE       company_id      IN %s
                            AND         payment_type    = 'inbound';
                         """, (tuple(self.company_ids.ids), ))
        _logger.info(u"Company Deletion - Companies %s - Customer Payments - END" % company_ids)

        self.env.cr.commit()

        # On autorise l'annulation d'écritures sur tous les journaux des sociétés à supprimer
        journals = self.env['account.journal'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        journals.write({'update_posted': True})
        if hasattr(self.env['account.journal'], 'of_cancel_moves'):
            journals.write({'of_cancel_moves': True})
        if hasattr(self.env['account.journal'], 'journal_lock_date'):
            journals.write({'journal_lock_date': False})

        # Remises en banque
        if 'of.account.payment.bank.deposit' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Bank Deposits - START" % company_ids)
            # Seules les remises en banque brouillon ou annulées peuvent être supprimées
            self.env['of.account.payment.bank.deposit'].with_context(active_test=False).search(
                [('journal_id.company_id', 'in', self.company_ids.ids), ('state', '!=', 'draft')]).cancel()
            self.env['of.account.payment.bank.deposit'].with_context(active_test=False).search(
                [('journal_id.company_id', 'in', self.company_ids.ids)]).unlink()
            _logger.info(u"Company Deletion - Companies %s - Bank Deposits - END" % company_ids)

            self.env.cr.commit()

        # Rapprochements bancaires
        if 'of.account.bank.reconciliation' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Bank Reconciliations - START" % company_ids)
            self.env['of.account.bank.reconciliation'].with_context(active_test=False).search(
                [('company_id', 'in', self.company_ids.ids)]).unlink()
            _logger.info(u"Company Deletion - Companies %s - Bank Reconciliations - END" % company_ids)

            self.env.cr.commit()

        # Commandes fournisseur
        _logger.info(u"Company Deletion - Companies %s - Purchase Orders - START" % company_ids)
        # Seules les commandes brouillon ou annulées peuvent être supprimées
        self.env['purchase.order'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids), ('state', '!=', 'cancel')]).write({'state': 'cancel'})
        self.env['purchase.order'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Purchase Orders - END" % company_ids)

        self.env.cr.commit()

        # Ordres d'approvisionnement
        _logger.info(u"Company Deletion - Companies %s - Procurement Orders - START" % company_ids)
        procurement_orders = self.env['procurement.order'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        # Seuls les ordres d'approvisionnement en exception peuvent être supprimés
        procurement_orders.write({'state': 'exception'})
        procurement_orders.unlink()
        _logger.info(u"Company Deletion - Companies %s - Procurement Orders - END" % company_ids)

        self.env.cr.commit()

        # Factures fournisseur
        _logger.info(u"Company Deletion - Companies %s - Supplier Invoices - START" % company_ids)
        account_invoices = self.env['account.invoice'].with_context(active_test=False).search(
            [('type', 'in', ['in_invoice', 'in_refund']),
             ('company_id', 'in', self.company_ids.ids)])
        # Seules les factures brouillon ou annulées qui n'ont pas de numéro attribué peuvent être supprimées
        account_invoices.write({'state': 'cancel', 'move_name': False})
        account_invoices.unlink()
        _logger.info(u"Company Deletion - Companies %s - Supplier Invoices - END" % company_ids)

        self.env.cr.commit()

        # Paiements fournisseur
        _logger.info(u"Company Deletion - Companies %s - Supplier Payments - START" % company_ids)
        # Suppression des historiques de paiement
        if 'of.log.paiement' in self.env:
            self._cr.execute("""DELETE FROM of_log_paiement
                                WHERE       paiement_id     IN (    SELECT  id
                                                                    FROM    account_payment
                                                                    WHERE   company_id      IN %s
                                                                    AND     payment_type    = 'outbound'
                                                                );
                             """, (tuple(self.company_ids.ids), ))
        self._cr.execute("""DELETE FROM account_payment
                            WHERE       company_id      IN %s
                            AND         payment_type    = 'outbound';
                         """, (tuple(self.company_ids.ids), ))
        _logger.info(u"Company Deletion - Companies %s - Supplier Payments - END" % company_ids)

        self.env.cr.commit()

        # Autres paiements
        _logger.info(u"Company Deletion - Companies %s - Other Payments - START" % company_ids)
        # Suppression des historiques de paiement
        if 'of.log.paiement' in self.env:
            self._cr.execute("""DELETE FROM of_log_paiement
                                WHERE       paiement_id     IN (    SELECT  id
                                                                    FROM    account_payment
                                                                    WHERE   company_id      IN %s
                                                                );
                             """, (tuple(self.company_ids.ids),))
        self._cr.execute("""DELETE FROM account_payment
                            WHERE       company_id      IN %s;
                         """, (tuple(self.company_ids.ids),))
        _logger.info(u"Company Deletion - Companies %s - Other Payments - END" % company_ids)

        self.env.cr.commit()

        # Pièces comptables
        _logger.info(u"Company Deletion - Companies %s - Account Moves - START" % company_ids)
        account_moves = self.env['account.move'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        account_move_lines = account_moves.mapped('line_ids')
        # On supprime les lettrages potentiels sur les écritures à supprimer
        account_move_lines.remove_move_reconcile()
        # On vide les dates de verrouillage comptable sur les sociétés à supprimer
        if hasattr(self.env['res.company'], 'permanent_lock_date'):
            self.company_ids.permanent_lock_date = False
        if hasattr(self.env['res.company'], 'fiscalyear_lock_date'):
            self.company_ids.fiscalyear_lock_date = False
        # Seules les pièces annulées peuvent être supprimées
        account_moves.button_cancel()
        # Des valeurs de débit mal arrondies à 0 empêchent la suppression des écritures
        lines_to_update = account_move_lines.filtered(lambda l: float_is_zero(l.debit, precision_rounding=5))
        if lines_to_update:
            self._cr.execute("""UPDATE  account_move_line
                                SET     debit               = 0.0
                                WHERE   id                  IN %s;
                             """, (tuple(lines_to_update.ids),))
        # Des valeurs de crédit mal arrondies à 0 empêchent la suppression des écritures
        lines_to_update = account_move_lines.filtered(lambda l: float_is_zero(l.credit, precision_rounding=5))
        if lines_to_update:
            self._cr.execute("""UPDATE  account_move_line
                                SET     credit              = 0.0
                                WHERE   id                  IN %s;
                             """, (tuple(lines_to_update.ids),))
        for move in account_moves:
            # Le module account surcharge la fonction unlink et provoque des temps de calcul qui explosent en
            # fonction du nombre de pièces comptables à supprimer.
            # L'appel de prefetch() permet de supprimer les pièces une par une et ainsi de garder un temps d'exécution
            # linéaire.
            move.with_prefetch().unlink()
        _logger.info(u"Company Deletion - Companies %s - Account Moves - END" % company_ids)

        self.env.cr.commit()

        # Propriétés
        _logger.info(u"Company Deletion - Companies %s - Properties - START" % company_ids)
        self.env['ir.property'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Properties - END" % company_ids)

        self.env.cr.commit()

        # Modes de paiement
        if 'of.account.payment.mode' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Payment Modes - START" % company_ids)
            self.env['of.account.payment.mode'].with_context(active_test=False).search(
                [('company_id', 'in', self.company_ids.ids)]).unlink()
            _logger.info(u"Company Deletion - Companies %s - Payment Modes - END" % company_ids)

            self.env.cr.commit()

        # Journaux
        _logger.info(u"Company Deletion - Companies %s - Account Journals - START" % company_ids)
        self.env['account.journal'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Account Journals - END" % company_ids)

        self.env.cr.commit()

        # Positions fiscales
        _logger.info(u"Company Deletion - Companies %s - Fiscal Positions - START" % company_ids)
        self.env['account.fiscal.position'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Fiscal Positions - END" % company_ids)

        self.env.cr.commit()

        # Taxes
        _logger.info(u"Company Deletion - Companies %s - Taxes - START" % company_ids)
        self.env['account.tax'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Taxes - END" % company_ids)

        self.env.cr.commit()

        # Plans comptables
        _logger.info(u"Company Deletion - Companies %s - Accounts - START" % company_ids)
        accounts = self.env['account.account'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        # Dans le cas où des propriétés des partenaires sur les comptes comptables à supprimer existent toujours
        # (i.e. des propriétés d'une société portant sur un compte d'une autre société), on supprime les affectations
        values = ['account.account,%s' % (account_id,) for account_id in accounts.ids]
        self.env['ir.property'].search([('value_reference', 'in', values)]).unlink()
        accounts.unlink()
        _logger.info(u"Company Deletion - Companies %s - Accounts - END" % company_ids)

        self.env.cr.commit()

        # Comptes analytiques
        _logger.info(u"Company Deletion - Companies %s - Analytic Accounts - START" % company_ids)
        analytic_accounts = self.env['account.analytic.account'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        if 'project.project' in self.env:
            # Suppression des projets et tâches associés aux comptes analytiques à supprimer
            projects = self.env['project.project'].with_context(active_test=False).search(
                [('analytic_account_id', 'in', analytic_accounts.ids)])
            self.env['project.task'].with_context(active_test=False).search(
                [('project_id', 'in', projects.ids)]).unlink()
            projects.unlink()
        analytic_accounts.unlink()
        _logger.info(u"Company Deletion - Companies %s - Analytic Accounts - END" % company_ids)

        self.env.cr.commit()

        # Contrats analytiques
        if 'account.analytic.contract' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Analytic Contracts - START" % company_ids)
            self.env['account.analytic.contract'].with_context(active_test=False).search(
                [('company_id', 'in', self.company_ids.ids)]).unlink()
            _logger.info(u"Company Deletion - Companies %s - Analytic Contracts - END" % company_ids)

            self.env.cr.commit()

        # RDVs d'intervention
        if 'of.planning.intervention' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Planning Interventions - START" % company_ids)
            self.env['of.planning.intervention'].with_context(active_test=False).search(
                [('company_id', 'in', self.company_ids.ids)]).unlink()
            _logger.info(u"Company Deletion - Companies %s - Planning Interventions - END" % company_ids)

            self.env.cr.commit()

        # Demandes d'intervention
        if 'of.service' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Ponctual Services - START" % company_ids)
            self.env['of.service'].with_context(active_test=False).search(
                [('recurrence', '=', False),
                 ('company_id', 'in', self.company_ids.ids)]).unlink()
            _logger.info(u"Company Deletion - Companies %s - Ponctual Services - END" % company_ids)

            self.env.cr.commit()

        # Contrats d'entretien
        if 'of.service' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Recurrent Services - START" % company_ids)
            self.env['of.service'].with_context(active_test=False).search(
                [('recurrence', '=', True),
                 ('company_id', 'in', self.company_ids.ids)]).unlink()
            _logger.info(u"Company Deletion - Companies %s - Recurrent Services - END" % company_ids)

            self.env.cr.commit()

        # SAVs
        _logger.info(u"Company Deletion - Companies %s - Project Issues - START" % company_ids)
        self.env['project.issue'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Project Issues - END" % company_ids)

        self.env.cr.commit()

        # Parcs installés
        if 'of.parc.installe' in self.env:
            _logger.info(u"Company Deletion - Companies %s - Parcs Installés - START" % company_ids)
            if 'company_id' in self.env['of.parc.installe']:
                parc_installes = self.env['of.parc.installe'].with_context(active_test=False).search(
                    [('company_id', 'in', self.company_ids.ids)])
                parc_installes |= self.env['of.parc.installe'].with_context(active_test=False).search(
                    [('company_id', '=', False), ('client_id.company_id', 'in', self.company_ids.ids)])
            else:
                parc_installes = self.env['of.parc.installe'].with_context(active_test=False).search(
                    [('client_id.company_id', 'in', self.company_ids.ids)])
            # Si des parcs installés à supprimer sont rattachés à des SAVs, on supprime ce lien
            self.env['project.issue'].with_context(active_test=False).search(
                [('of_produit_installe_id', 'in', parc_installes.ids)]).write({'of_produit_installe_id': False})
            parc_installes.unlink()
            _logger.info(u"Company Deletion - Companies %s - Parcs Installés - END" % company_ids)

            self.env.cr.commit()

        # Mouvements de stock
        _logger.info(u"Company Deletion - Companies %s - Stock Moves - START" % company_ids)
        self._cr.execute("""DELETE FROM stock_move
                            WHERE       company_id  IN %s;
                         """, (tuple(self.company_ids.ids), ))
        # Suppression des quants associés
        self._cr.execute("""DELETE FROM stock_quant
                            WHERE       company_id  IN %s;
                         """, (tuple(self.company_ids.ids), ))
        _logger.info(u"Company Deletion - Companies %s - Stock Moves - END" % company_ids)

        self.env.cr.commit()

        # Bons de livraison
        _logger.info(u"Company Deletion - Companies %s - Delivery Pickings - START" % company_ids)
        # Suppression des opérations de stock associées aux BL à supprimer
        self._cr.execute(
            """DELETE FROM stock_pack_operation
               WHERE       picking_id           IN (    SELECT  SP.id
                                                        FROM    stock_picking       SP
                                                        ,       stock_picking_type  SPT
                                                        WHERE   SP.company_id       IN %s
                                                        AND     SPT.id              = SP.picking_type_id
                                                        AND     SPT.code            = 'outgoing'
                                                    );
            """, (tuple(self.company_ids.ids), ))
        self.env['stock.picking'].with_context(active_test=False).search(
            [('picking_type_id.code', '=', 'outgoing'),
             ('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Delivery Pickings - END" % company_ids)

        self.env.cr.commit()

        # Bons de réception
        _logger.info(u"Company Deletion - Companies %s - Receipt Pickings - START" % company_ids)
        # Suppression des opérations de stock associées aux BR à supprimer
        self._cr.execute(
            """DELETE FROM stock_pack_operation
               WHERE       picking_id           IN (    SELECT  SP.id
                                                        FROM    stock_picking       SP
                                                        ,       stock_picking_type  SPT
                                                        WHERE   SP.company_id       IN %s
                                                        AND     SPT.id              = SP.picking_type_id
                                                        AND     SPT.code            = 'incoming'
                                                    );
            """, (tuple(self.company_ids.ids), ))
        self.env['stock.picking'].with_context(active_test=False).search(
            [('picking_type_id.code', '=', 'incoming'),
             ('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Receipt Pickings - END" % company_ids)

        self.env.cr.commit()

        # Entrepôts
        _logger.info(u"Company Deletion - Companies %s - Stock Warehouses - START" % company_ids)
        # S'il reste des transferts (BL, BR ou BT) associés à des entrepôts à supprimer, on les supprime
        warehouse_pickings = self.env['stock.picking'].with_context(active_test=False).search(
            ['|',
             ('location_id.company_id', 'in', self.company_ids.ids),
             ('location_dest_id.company_id', 'in', self.company_ids.ids)])
        if warehouse_pickings:
            # Suppression des opérations de stock associées aux transferts à supprimer
            self._cr.execute(
                """DELETE FROM stock_pack_operation
                   WHERE       picking_id           IN %s;
                """, (tuple(warehouse_pickings.ids),))
            warehouse_pickings.unlink()
        # Suppression des règles d'approvisionnement associées aux entrepôts à supprimer
        self.env['procurement.rule'].with_context(active_test=False).search(
            [('warehouse_id.company_id', 'in', self.company_ids.ids)]).unlink()
        # Si un bon de commande est accocié à un entrepôt à supprimer, on le remplace par le bon de commande
        # par défaut pour sa société
        for vals in self.env['sale.order'].with_context(active_test=False).read_group(
                [('warehouse_id.company_id', 'in', self.company_ids.ids)], 'company_id', 'company_id'):
            if vals['company_id']:
                # Code récupéré de sale.order._default_warehouse_id() (module sale_stock)
                default_warehouse_id = self.env['stock.warehouse'].search(
                    [('company_id', '=', vals['company_id'][0])], limit=1).id
                self.env['sale.order'].with_context(active_test=False).search(vals['__domain']).write(
                    {'warehouse_id': default_warehouse_id})
            else:
                # Suppression des commandes sans société mais avec un entrepôt erroné
                orders = self.env['sale.order'].with_context(active_test=False).search(vals['__domain'])
                orders.filtered(lambda o: o.state not in ('draft', 'cancel')).write({'state': 'cancel'})
                orders.unlink()
        # Si les entrepôts à supprimer sont utilisés comme entrepôt par défaut sur des sociétés,
        # on modifie les sociétés pour y mettre un autre entrepôt arbitrairement
        warehouses = self.env['stock.warehouse'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        other_warehouse = self.env['stock.warehouse'].search([('company_id', 'not in', self.company_ids.ids)], limit=1)
        self.env['res.company'].search([('of_default_warehouse_id', 'in', warehouses.ids)]).write(
            {'of_default_warehouse_id': other_warehouse.id})
        warehouses.unlink()
        _logger.info(u"Company Deletion - Companies %s - Stock Warehouses - END" % company_ids)

        self.env.cr.commit()

        # Emplacements de stock
        _logger.info(u"Company Deletion - Companies %s - Stock Locations - START" % company_ids)
        # Suppression des inventaires de stock associés aux emplacements à supprimer
        stock_inventories = self.env['stock.inventory'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        # Seuls les inventaires brouillon ou annulés peuvent être supprimés
        stock_inventories.action_cancel_draft()
        stock_inventories.unlink()
        # Suppression des rebuts de stock associés aux emplacements à supprimer
        stock_scraps = self.env['stock.scrap'].with_context(active_test=False).search(
            ['|',
             ('location_id.company_id', 'in', self.company_ids.ids),
             ('scrap_location_id.company_id', 'in', self.company_ids.ids)])
        # Seuls les rebuts brouillon peuvent être supprimés
        stock_scraps.write({'state': 'draft'})
        stock_scraps.unlink()
        self.env['stock.location'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        _logger.info(u"Company Deletion - Companies %s - Stock Locations - END" % company_ids)

        self.env.cr.commit()

        # Séquences
        _logger.info(u"Company Deletion - Companies %s - Sequences - START" % company_ids)
        sequences = self.env['ir.sequence'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        # S'il reste des type d'opération de stock associés à des séquences à supprimer, on vide la société de la
        # séquence et on ne la supprime pas
        picking_types = self.env['stock.picking.type'].with_context(active_test=False).search(
            [('sequence_id', 'in', sequences.ids), ('warehouse_id.company_id', 'not in', self.company_ids.ids)])
        if picking_types:
            picking_sequences = picking_types.mapped('sequence_id')
            picking_sequences.write({'company_id': False})
            sequences -= picking_sequences
        sequences.unlink()
        _logger.info(u"Company Deletion - Companies %s - Sequences - END" % company_ids)

        self.env.cr.commit()

        # Utilisateurs
        _logger.info(u"Company Deletion - Companies %s - Users - START" % company_ids)
        company_users = self.env['res.users'].with_context(active_test=False).search(
            [('company_ids', 'in', self.company_ids.ids)])
        # Si les utilisateurs ont d'autres sociétés autorisées que celles à supprimer, on retire simplement les
        # sociétés à supprimer de leurs sociétés autorisées, et on change leur société courante si besoin
        for user in company_users:
            if user.company_ids - self.company_ids:
                company_users -= user
                if user.company_id.id in self.company_ids.ids:
                    user.company_id = user.company_ids.filtered(lambda comp: comp.id not in self.company_ids.ids)[0]
        # Suppression des activités CRM associées à des utilisateurs à supprimer
        if 'of.crm.activity' in self.env:
            self.env['of.crm.activity'].with_context(active_test=False).search(
                ['|', ('user_id', 'in', company_users.ids), ('vendor_id', 'in', company_users.ids)]).unlink()
        company_users.unlink()
        _logger.info(u"Company Deletion - Companies %s - Users - END" % company_ids)

        self.env.cr.commit()

        # Partenaires
        _logger.info(u"Company Deletion - Companies %s - Partners - START" % company_ids)
        company_partners = self.env['res.partner'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        # On ne supprime aucun fournisseur, on vide simplement leur société
        suppliers = company_partners.filtered(lambda p: p.supplier)
        if suppliers:
            company_partners -= suppliers
            suppliers.write({'company_id': False})
        # On ne supprime pas les partenaires correspondant à des sociétés, on vide simplement leur société
        for company in self.company_ids:
            company_partner = company.partner_id
            if company_partner.id in company_partners.ids:
                company_partners -= company_partner
                company_partner.write({'company_id': False})
        # On ne supprime pas les partenaires correspondant à des marques, on vide simplement leur société
        if 'of.product.brand' in self.env:
            brand_partners = self.env['of.product.brand'].with_context(active_test=False).search(
                [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
            if brand_partners:
                company_partners -= brand_partners
                brand_partners.write({'company_id': False})
        # On ne supprime pas les partenaires qui ont encore des factures, on vide simplement leur société
        invoice_partners = self.env['account.invoice'].with_context(active_test=False).search(
            [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
        if invoice_partners:
            company_partners -= invoice_partners
            invoice_partners.write({'company_id': False})
        # On ne supprime pas les partenaires qui ont encore des commandes de vente, on vide simplement leur société
        so_partners = self.env['sale.order'].with_context(active_test=False).search(
            [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
        so_partners |= self.env['sale.order'].with_context(active_test=False).search(
            [('partner_invoice_id', 'in', company_partners.ids)]).mapped('partner_invoice_id')
        so_partners |= self.env['sale.order'].with_context(active_test=False).search(
            [('partner_shipping_id', 'in', company_partners.ids)]).mapped('partner_shipping_id')
        if so_partners:
            company_partners -= so_partners
            so_partners.write({'company_id': False})
        # On ne supprime pas les partenaires qui ont encore des commandes d'achat, on vide simplement leur société
        po_partners = self.env['purchase.order'].with_context(active_test=False).search(
            [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
        if po_partners:
            company_partners -= po_partners
            po_partners.write({'company_id': False})
        # On ne supprime pas les partenaires correspondant à des utilisateurs, on vide simplement leur société
        user_partners = self.env['res.users'].with_context(active_test=False).search(
            [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
        if user_partners:
            company_partners -= user_partners
            user_partners.write({'company_id': False})
        # On ne supprime pas les partenaires qui ont encore des savs, on vide simplement leur société
        project_issue_partners = self.env['project.issue'].with_context(active_test=False).search(
            [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
        if project_issue_partners:
            company_partners -= project_issue_partners
            project_issue_partners.write({'company_id': False})
        # On ne supprime pas les partenaires qui ont encore des parcs installés, on vide simplement leur société
        if 'of.parc.installe' in self.env:
            parc_installe_partners = self.env['of.parc.installe'].with_context(active_test=False).search(
                [('client_id', 'in', company_partners.ids)]).mapped('client_id')
            if parc_installe_partners:
                company_partners -= parc_installe_partners
                parc_installe_partners.write({'company_id': False})
        # On ne supprime pas les partenaires qui ont encore des interventions, on vide simplement leur société
        if 'of.service' in self.env:
            service_partners = self.env['of.service'].with_context(active_test=False).search(
                [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
            service_partners |= self.env['of.service'].with_context(active_test=False).search(
                [('address_id', 'in', company_partners.ids)]).mapped('address_id')
            if service_partners:
                company_partners -= service_partners
                service_partners.write({'company_id': False})
        # On ne supprime pas les partenaires qui ont encore des écritures comptables, on vide simplement leur société
        account_move_partners = self.env['account.move.line'].with_context(active_test=False).search(
            [('partner_id', 'in', company_partners.ids)]).mapped('partner_id')
        if account_move_partners:
            company_partners -= account_move_partners
            account_move_partners.write({'company_id': False})
        # Suppression des contacts calendriers associés à des partenaires à supprimer
        self.env['calendar.contacts'].with_context(active_test=False).search(
            [('partner_id', 'in', company_partners.ids)]).unlink()
        company_partners.unlink()
        _logger.info(u"Company Deletion - Companies %s - Partners - END" % company_ids)

        self.env.cr.commit()

        # Employés
        _logger.info(u"Company Deletion - Companies %s - Employees - START" % company_ids)
        # Suppression des objectifs de vente associés à des sociétés à supprimer, si le modèle existe
        if 'of.sale.objective' in self.env:
            self.env['of.sale.objective'].with_context(active_test=False).search(
                [('company_id', 'in', self.company_ids.ids)]).unlink()
        employees = self.env['hr.employee'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        # Suppression des lignes d'objectif de vente associées à des employés à supprimer, si le modèle existe
        if 'of.sale.objective.line' in self.env:
            self.env['of.sale.objective.line'].with_context(active_test=False).search(
                [('employee_id', 'in', employees.ids)]).unlink()
        employees.unlink()
        _logger.info(u"Company Deletion - Companies %s - Employees - END" % company_ids)

        self.env.cr.commit()

        # Société
        # Suppression des historiques de prix d'article associés à des sociétés à supprimer
        self.env['product.price.history'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).unlink()
        # S'il existe des conditions de règlement associées à des sociétés à supprimer, on leur affecte une autre
        # société arbitrairement
        other_company = self.env['res.company'].search([('id', 'not in', self.company_ids.ids)], limit=1)
        self.env['account.payment.term'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).write({'company_id': other_company.id})
        # Suppression des modèles de taxe et de leurs relations avec des modèles de positions fiscales, associés à des
        # sociétés à supprimer
        tax_templates = self.env['account.tax.template'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)])
        self.env['account.fiscal.position.tax.template'].with_context(active_test=False).search(
            [('tax_src_id', 'in', tax_templates.ids)]).unlink()
        tax_templates.unlink()
        # S'il existe des intermédiaires de paiement associés à des sociétés à supprimer, on leur affecte une autre
        # société arbitrairement
        self.env['payment.acquirer'].with_context(active_test=False).search(
            [('company_id', 'in', self.company_ids.ids)]).write({'company_id': other_company.id})
        self.company_ids.unlink()

        _logger.info(u"Company Deletion - Companies %s - END" % company_ids)

        _logger.info(u"Company Deletion - END")

        # On renvoie sur la vue liste des sociétés
        action = self.env.ref('base.action_res_company_form').read()[0]
        action['target'] = 'main'
        return action
