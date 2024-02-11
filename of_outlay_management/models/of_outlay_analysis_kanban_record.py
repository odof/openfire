# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

RECORD_TYPES = [('01_products', u"Produits"),
                ('02_costs', u"Charges"),
                ('03_gross_margin', u"Marge brute"),
                ('04_time', u"Temps"),
                ('05_net_margin', u"Marge nette")]

RECORD_CATEGORIES = [('01_initial', u"Budget initial"),
                     ('02_complementary', u"Budget complémentaire"),
                     ('03_involved', u"Budget engagé"),
                     ('04_current', u"Situation en cours"),
                     ('05_progress', u"Avancement"),
                     ('06_invoiced', u"Facturé"),
                     ('07_final', u"Situation finale"),]


class OFOutlayAnalysisKanbanRecord(models.Model):
    _name = 'of.outlay.analysis.kanban.record'
    _description = u"Enregistrement Kanban pour l'analyse de débours"
    _order = "type"

    analysis_id = fields.Many2one(comodel_name='of.outlay.analysis', string=u"Analyse de débours", required=True)
    type = fields.Selection(selection=RECORD_TYPES, string=u"Type", required=True)
    category = fields.Selection(selection=RECORD_CATEGORIES, string=u"Catégorie", required=True, readonly=True)
    value1 = fields.Char(string=u"Valeur 1")
    value2 = fields.Char(string=u"Valeur 2")
    value3 = fields.Char(string=u"Valeur 3")
    value4 = fields.Char(string=u"Valeur 4")
    label1 = fields.Char(string=u"Libellé 1")
    label2 = fields.Char(string=u"Libellé 2")
    label3 = fields.Char(string=u"Libellé 3")
    label4 = fields.Char(string=u"Libellé 4")
    main_color = fields.Char(string=u"Couleur principale")
    color1 = fields.Char(string=u"Couleur 1", default="#000000")
    color2 = fields.Char(string=u"Couleur 2", default="#000000")
    color3 = fields.Char(string=u"Couleur 3", default="#000000")
    color4 = fields.Char(string=u"Couleur 4", default="#000000")

    @api.model
    def recompute_records(self, analysis):
        # Delete existing records
        analysis.kanban_record_ids.unlink()

        # Initial budget
        init_budget_categ = '01_initial'
        init_budget_color = '#0ca789'
        self.create({'analysis_id': analysis.id,
                     'type': '01_products',
                     'category': init_budget_categ,
                     'main_color': init_budget_color,
                     'value1': '{:,.0f}'.format(200000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Dont produits :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Dont services :",
                     'value4': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '02_costs',
                     'category': init_budget_categ,
                     'main_color': init_budget_color,
                     'value1': '{:,.0f}'.format(120000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Dont achats :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Dont sous-traitance :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '03_gross_margin',
                     'category': init_budget_categ,
                     'main_color': init_budget_color,
                     'label1': u"Réelle",
                     'value1': '{:,.0f}'.format(38).replace(',', ' ').replace('.', ',') + u" %",
                     'label2': u"Obj.",
                     'value2': '{:,.0f}'.format(40).replace(',', ' ').replace('.', ',') + u" %",
                     'label3': u"Réelle :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Obj. :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '04_time',
                     'category': init_budget_categ,
                     'main_color': init_budget_color,
                     'label1': u"Heures",
                     'value1': '{:,.0f}'.format(500).replace(',', ' ').replace('.', ','),
                     'label2': u"Valo.",
                     'value2': '{:,.0f}'.format(3000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '05_net_margin',
                     'category': init_budget_categ,
                     'main_color': init_budget_color,
                     'value1': '{:,.0f}'.format(3).replace(',', ' ').replace('.', ',') + u" %",
                     'value2': '{:,.0f}'.format(50000).replace(',', ' ').replace('.', ',') + u" €",
                     })

        # Complementary budget
        compl_budget_categ = '02_complementary'
        compl_budget_color = '#3db9a1'
        self.create({'analysis_id': analysis.id,
                     'type': '01_products',
                     'category': compl_budget_categ,
                     'main_color': compl_budget_color,
                     'value1': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Dont produits :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Dont services :",
                     'value4': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '02_costs',
                     'category': compl_budget_categ,
                     'main_color': compl_budget_color,
                     'value1': '{:,.0f}'.format(120000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Dont achats :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Dont sous-traitance :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '03_gross_margin',
                     'category': compl_budget_categ,
                     'main_color': compl_budget_color,
                     'label1': u"Réelle",
                     'value1': '{:,.0f}'.format(38).replace(',', ' ').replace('.', ',') + u" %",
                     'label2': u"Obj.",
                     'value2': '{:,.0f}'.format(40).replace(',', ' ').replace('.', ',') + u" %",
                     'label3': u"Réelle :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Obj. :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '04_time',
                     'category': compl_budget_categ,
                     'main_color': compl_budget_color,
                     'label1': u"Heures",
                     'value1': '{:,.0f}'.format(500).replace(',', ' ').replace('.', ','),
                     'label2': u"Valo.",
                     'value2': '{:,.0f}'.format(3000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '05_net_margin',
                     'category': compl_budget_categ,
                     'main_color': compl_budget_color,
                     'value1': '{:,.0f}'.format(3).replace(',', ' ').replace('.', ',') + u" %",
                     'value2': '{:,.0f}'.format(50000).replace(',', ' ').replace('.', ',') + u" €",
                     })

        # Involved budget
        inv_budget_categ = '03_involved'
        inv_budget_color = '#85d3c4'
        self.create({'analysis_id': analysis.id,
                     'type': '01_products',
                     'category': inv_budget_categ,
                     'main_color': inv_budget_color,
                     'value1': '{:,.0f}'.format(200000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Dont produits :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Dont services :",
                     'value4': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '02_costs',
                     'category': inv_budget_categ,
                     'main_color': inv_budget_color,
                     'value1': '{:,.0f}'.format(120000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Dont achats :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Dont stocks consommés :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '03_gross_margin',
                     'category': inv_budget_categ,
                     'main_color': inv_budget_color,
                     'label1': u"Réelle",
                     'value1': '{:,.0f}'.format(38).replace(',', ' ').replace('.', ',') + u" %",
                     'label2': u"Obj.",
                     'value2': '{:,.0f}'.format(40).replace(',', ' ').replace('.', ',') + u" %",
                     'label3': u"Réelle :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Obj. :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '04_time',
                     'category': inv_budget_categ,
                     'main_color': inv_budget_color,
                     'label1': u"Heures",
                     'value1': '{:,.0f}'.format(500).replace(',', ' ').replace('.', ','),
                     'label2': u"Valo.",
                     'value2': '{:,.0f}'.format(3000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '05_net_margin',
                     'category': inv_budget_categ,
                     'main_color': inv_budget_color,
                     'value1': '{:,.0f}'.format(3).replace(',', ' ').replace('.', ',') + u" %",
                     'value2': '{:,.0f}'.format(50000).replace(',', ' ').replace('.', ',') + u" €",
                     })

        # Current situation
        curr_situation_categ = '04_current'
        curr_situation_color = '#fef9a2'
        self.create({'analysis_id': analysis.id,
                     'type': '01_products',
                     'category': curr_situation_categ,
                     'main_color': curr_situation_color,
                     'value1': '{:,.0f}'.format(180000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(80).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '02_costs',
                     'category': curr_situation_categ,
                     'main_color': curr_situation_color,
                     'value1': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(80).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '03_gross_margin',
                     'category': curr_situation_categ,
                     'main_color': curr_situation_color,
                     'label1': u"Réelle",
                     'value1': '{:,.0f}'.format(38).replace(',', ' ').replace('.', ',') + u" %",
                     'label2': u"Obj.",
                     'value2': '{:,.0f}'.format(40).replace(',', ' ').replace('.', ',') + u" %",
                     'label3': u"Réelle :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Obj. :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '04_time',
                     'category': curr_situation_categ,
                     'main_color': curr_situation_color,
                     'label1': u"Heures",
                     'value1': '{:,.0f}'.format(500).replace(',', ' ').replace('.', ','),
                     'label2': u"Valo.",
                     'value2': '{:,.0f}'.format(3000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '05_net_margin',
                     'category': curr_situation_categ,
                     'main_color': curr_situation_color,
                     'value1': '{:,.0f}'.format(3).replace(',', ' ').replace('.', ',') + u" %",
                     'value2': '{:,.0f}'.format(50000).replace(',', ' ').replace('.', ',') + u" €",
                     })

        # Progress
        progress_categ = '05_progress'
        progress_color = '#fef9a2'
        self.create({'analysis_id': analysis.id,
                     'type': '01_products',
                     'category': progress_categ,
                     'main_color': progress_color,
                     'value1': '{:,.0f}'.format(180000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(80).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '02_costs',
                     'category': progress_categ,
                     'main_color': progress_color,
                     'value1': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(80).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '03_gross_margin',
                     'category': progress_categ,
                     'main_color': progress_color,
                     'label1': u"Réelle",
                     'value1': '{:,.0f}'.format(38).replace(',', ' ').replace('.', ',') + u" %",
                     'label2': u"Obj.",
                     'value2': '{:,.0f}'.format(40).replace(',', ' ').replace('.', ',') + u" %",
                     'label3': u"Réelle :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Obj. :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '04_time',
                     'category': progress_categ,
                     'main_color': progress_color,
                     'label1': u"Heures",
                     'value1': '{:,.0f}'.format(500).replace(',', ' ').replace('.', ','),
                     'label2': u"Valo.",
                     'value2': '{:,.0f}'.format(3000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '05_net_margin',
                     'category': progress_categ,
                     'main_color': progress_color,
                     'value1': '{:,.0f}'.format(3).replace(',', ' ').replace('.', ',') + u" %",
                     'value2': '{:,.0f}'.format(50000).replace(',', ' ').replace('.', ',') + u" €",
                     })

        # Invoiced
        invoiced_categ = '06_invoiced'
        invoiced_color = '#b6e4db'
        self.create({'analysis_id': analysis.id,
                     'type': '01_products',
                     'category': invoiced_categ,
                     'main_color': invoiced_color,
                     'label1': u"À date",
                     'value1': '{:,.0f}'.format(120000).replace(',', ' ').replace('.', ',') + u" €",
                     'label2': u"FAE",
                     'value2': '{:,.0f}'.format(6000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(60).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '02_costs',
                     'category': invoiced_categ,
                     'main_color': invoiced_color,
                     'label1': u"À date",
                     'value1': '{:,.0f}'.format(120000).replace(',', ' ').replace('.', ',') + u" €",
                     'label2': u"Gap",
                     'value2': '{:,.0f}'.format(6000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(60).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '03_gross_margin',
                     'category': invoiced_categ,
                     'main_color': invoiced_color,
                     'label1': u"Réelle",
                     'value1': '{:,.0f}'.format(38).replace(',', ' ').replace('.', ',') + u" %",
                     'label2': u"Obj.",
                     'value2': '{:,.0f}'.format(40).replace(',', ' ').replace('.', ',') + u" %",
                     'label3': u"Réelle :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Obj. :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '04_time',
                     'category': invoiced_categ,
                     'main_color': invoiced_color,
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '05_net_margin',
                     'category': invoiced_categ,
                     'main_color': invoiced_color,
                     'value1': '{:,.0f}'.format(3).replace(',', ' ').replace('.', ',') + u" %",
                     'value2': '{:,.0f}'.format(50000).replace(',', ' ').replace('.', ',') + u" €",
                     })

        # Final situation
        final_situation_categ = '07_final'
        final_situation_color = '#b6e4db'
        self.create({'analysis_id': analysis.id,
                     'type': '01_products',
                     'category': final_situation_categ,
                     'main_color': final_situation_color,
                     'label1': u"À date",
                     'value1': '{:,.0f}'.format(120000).replace(',', ' ').replace('.', ',') + u" €",
                     'label2': u"FAE",
                     'value2': '{:,.0f}'.format(6000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(60).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '02_costs',
                     'category': final_situation_categ,
                     'main_color': final_situation_color,
                     'label1': u"À date",
                     'value1': '{:,.0f}'.format(120000).replace(',', ' ').replace('.', ',') + u" €",
                     'label2': u"Gap",
                     'value2': '{:,.0f}'.format(6000).replace(',', ' ').replace('.', ',') + u" €",
                     'label3': u"Avancement :",
                     'value3': '{:,.2f}'.format(60).replace(',', ' ').replace('.', ',') + u" %",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '03_gross_margin',
                     'category': final_situation_categ,
                     'main_color': final_situation_color,
                     'label1': u"Réelle",
                     'value1': '{:,.0f}'.format(38).replace(',', ' ').replace('.', ',') + u" %",
                     'label2': u"Obj.",
                     'value2': '{:,.0f}'.format(40).replace(',', ' ').replace('.', ',') + u" %",
                     'label3': u"Réelle :",
                     'value3': '{:,.0f}'.format(100000).replace(',', ' ').replace('.', ',') + u" €",
                     'label4': u"Obj. :",
                     'value4': '{:,.0f}'.format(20000).replace(',', ' ').replace('.', ',') + u" €",
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '04_time',
                     'category': final_situation_categ,
                     'main_color': final_situation_color,
                     })
        self.create({'analysis_id': analysis.id,
                     'type': '05_net_margin',
                     'category': final_situation_categ,
                     'main_color': final_situation_color,
                     'value1': '{:,.0f}'.format(3).replace(',', ' ').replace('.', ',') + u" %",
                     'value2': '{:,.0f}'.format(50000).replace(',', ' ').replace('.', ',') + u" €",
                     })
