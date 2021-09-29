odoo.define('of_retail_analysis.ks_dashboard_custom', function (require) {
    "use strict";

    var Model = require('web.DataModel');
    var KsDashBoardNinja = require('ks_dashboard_ninja.ks_dashboard');

    KsDashBoardNinja.include({

        willStart: function() {
            var self = this;
            // récupérer les info pour l'affichage du bouton de filtrage par type et par secteur de société
            var ir_values_model = new Model("ir.values");
            var company_type_fils_def = new Model("of.res.company.type").call("get_company_type_filter_ids", []);
            var company_sector_fils_def = new Model("of.res.company.sector").call("get_company_sector_filter_ids", []);
            return $.when(company_type_fils_def, company_sector_fils_def, self._super())
            .then(function(company_type_filters, company_sector_filters){
                // filtres type société
                self.company_type_filters = company_type_filters;

                self.company_type_ids_indexes = {}
                var company_type_fil;
                // On place le current ici car on veut que de base le filtre soit en position "Tous"
                self.company_type_filters.push({id: 0, name: "Tous", current: true})
                for (var k=0; k<self.company_type_filters.length; k++) {
                    company_type_fil = self.company_type_filters[k];
                    self.company_type_ids_indexes[company_type_fil.id] = k;
                    if (company_type_fil['current']) {
                        self.now_company_type_id = company_type_fil.id;
                        self.now_company_type_name = company_type_fil.name;
                    }
                }
                // filtres secteur société
                self.company_sector_filters = company_sector_filters;

                self.company_sector_ids_indexes = {}
                var company_sector_fil;
                // On place le current ici car on veut que de base le filtre soit en position "Tous"
                self.company_sector_filters.push({id: 0, name: "Tous", current: true})
                for (var l=0; l<self.company_sector_filters.length; l++) {
                    company_sector_fil = self.company_sector_filters[l];
                    self.company_sector_ids_indexes[company_sector_fil.id] = l;
                    if (company_sector_fil['current']) {
                        self.now_company_sector_id = company_sector_fil.id;
                        self.now_company_sector_name = company_sector_fil.name;
                    }
                }
                return $.when();
            });
        },

        getContext: function () {
            var self = this;
            var context = {
                of_company_type_id: self.now_company_type_id,
                of_company_sector_id: self.now_company_sector_id,
            }
            return Object.assign(context,self._super.apply(self, arguments))
        },

        get_ks_header_render_vals: function() {
            var self = this;
            // ajout des valeurs pour le rendu des boutons de filtrage par secteur et type de société
            var update_dict = {
                'company_type_filters': self.company_type_filters,
                'company_sector_filters': self.company_sector_filters,
                'now_company_type_name': self.now_company_type_name,
                'now_company_sector_name': self.now_company_sector_name}
            return _.extend(update_dict,self._super.apply(self, arguments));
        },

        ksRenderDashboard: function () {
            var self = this;
            self._super.apply(self, arguments);
            // attacher les events de click bouton de filtrage après le rendu du header
            self.$el.find(".of_company_type_filter").click(self.proxy(self.on_company_type_filter_clicked));
            self.$el.find(".of_company_sector_filter").click(self.proxy(self.on_company_sector_filter_clicked));
        },

        /**
        *  Gestionnaire pour le clique sur un filtre de type de société
        */
        on_company_type_filter_clicked: function(ev) {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            var self = this;
            this.now_company_type_id = parseInt(ev.currentTarget.id.substring(20), 10);
            this.now_company_type_name = this.company_type_filters[
                this.company_type_ids_indexes[this.now_company_type_id]].name;

            this.$el.find("#now_company_type_name").text(this.now_company_type_name);
             $.when(self.ks_fetch_data()).then(function () {
               self.ksUpdateDashboardItem(Object.keys(self.ks_dashboard_data.ks_item_data));
            });
        },
        /**
        *  Gestionnaire pour le clique sur un filtre de secteur de société
        */
        on_company_sector_filter_clicked: function(ev) {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            var self = this;
            this.now_company_sector_id = parseInt(ev.currentTarget.id.substring(22), 10);
            this.now_company_sector_name = this.company_sector_filters[
                this.company_sector_ids_indexes[this.now_company_sector_id]].name;

            this.$el.find("#now_company_sector_name").text(this.now_company_sector_name);
             $.when(self.ks_fetch_data()).then(function () {
               self.ksUpdateDashboardItem(Object.keys(self.ks_dashboard_data.ks_item_data));
            });
        },

    });

});
