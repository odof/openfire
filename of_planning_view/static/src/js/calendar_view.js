odoo.define('of_planning_view.calendar_view', function (require) {
"use strict";
/*---------------------------------------------------------
 * OpenFire calendar - créneaux dispos
 *---------------------------------------------------------*/

var core = require('web.core');
var CalendarView = require('web_calendar.CalendarView');
var Model = require('web.DataModel');
var formats = require("web.formats");

var QWeb = core.qweb;

var ATTENDEE_MODES = {
    "tech": "Technique",
    "com": "Commercial",
    "comtech": "Technique & Commercial",
};

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

CalendarView.include({
    willStart: function() {
        var self = this;
        var ir_values_model = new Model('ir.values');
        var attendee_mode_def = ir_values_model.call("get_default",
                                                     ["of.intervention.settings", "attendee_mode", false]);
        // de quelle couleur afficher les jours fériés?
        var color_jours_feries_def = ir_values_model.call(
            "get_default", ["of.intervention.settings", "color_jours_feries"]);
        // masquer les pictos de recherche et d'assignation de secteur?
        var ignorer_jours_feries_def = ir_values_model.call(
            "get_default", ["of.intervention.settings", "ignorer_jours_feries"]);

        return $.when(attendee_mode_def, color_jours_feries_def, ignorer_jours_feries_def,  this._super())
        .then(function (attendee_mode, color_jours_feries, ignorer_jours_feries) {
            // affecter le mode de planning (com, tech ou comtech)
            self.attendee_mode = attendee_mode || "comtech";
            self.attendee_mode_name = ATTENDEE_MODES[self.attendee_mode];
            // initialiser l'attendee_mode du view_manager
            self.view_manager.attendee_mode = self.attendee_mode;
            self.jours_feries_opt = {
                'ignorer_jours_feries': ignorer_jours_feries,
                'color_jours_feries': color_jours_feries,
            }
            return $.when();
        });
    },
    /**
     *  Quand l'attribut "show_all_attendees" est à 1, on charge tous les filtres au chargement de la vue
     *  plutôt que de les charger à chaque search
     */
    _init_all_filters: function () {
        var self = this;
        if (this.model != 'of.planning.intervention'){
            return this._super();
        }

        if (!self.config_model) {
            throw new Error("Attribut 'config_model' manquant dans la définition de la vue XML");
        }

        var dfd = $.Deferred();
        var p = dfd.promise();
        var Attendees = new Model(self.attendee_model);

        Attendees.query(
                ['id', self.color_ft_field, self.color_bg_field, 'of_est_intervenant', 'of_est_commercial',
                 'name', 'sequence']) // retrieve colors from db
            .order_by(['sequence'])
            .all()
            .then(function (attendees){
                self.all_filters = new Array(attendees.length);  // Array pour conserver l'ordre
                // dictionnaire de la forme {id: index_filtre}
                // pour accéder facilement à l'indexe du filtre à partir de l'id de l'attendee
                self.res_ids_indexes = {}
                var a, filter_item;
                for (var i=0; i<attendees.length; i++) {
                    a = attendees[i];
                    filter_item = {
                        label: a['name'],
                        color_bg: a[self.color_bg_field],
                        color_ft: a[self.color_ft_field],
                        est_intervenant: a['of_est_intervenant'],
                        est_commercial: a['of_est_commercial'],
                        value: a['id'],
                        input_id: a['id'] + "_input",
                        is_checked: true,
                        is_visible: false,
                        sequence: a['sequence'],
                        custom_colors: true,
                    }
                    self.all_filters[i] = filter_item;
                    self.res_ids_indexes[a['id']] = i;
                    // ne montrer que les filtres (à droite) qui passent le filtrage par société et type de planning
                    if ((self.attendee_mode == 'tech' && a['of_est_intervenant'])
                            || (self.attendee_mode == 'com' && a['of_est_commercial'])
                            || (self.attendee_mode == 'comtech'
                                && (a['of_est_intervenant'] || a['of_est_commercial']))) {
                        filter_item.is_visible = true;
                    }
                };
                var ir_values_model = new Model("ir.values");
                // récupérer la sélection (coché/décoché) des filtres de la dernière utilisation de la vue planning
                // par l'utilisateur. Les filtres cochés sont dans la variable filter_attendee_ids
                ir_values_model.call("get_default",
                                     [self.config_model, "of_filter_attendee_ids", false])
                .then(function (attendee_ids) {
                    if (typeof attendee_ids == "string") {  // transformer en tableau si besoin
                        attendee_ids = JSON.parse(attendee_ids)
                    }
                    // tout cocher si tout était décoché
                    if (isNullOrUndef(attendee_ids) || attendee_ids.length == 0) {
                        self.filter_attendee_ids = []
                        for (var j in self.all_filters) {
                            self.filter_attendee_ids.push(self.all_filters[j].value);
                        };
                    // code 6: [ (6, 0 [ids]) ]
                    }else if (attendee_ids[0].length == 3 && attendee_ids[0][0] == 6 && !attendee_ids[0][1]) {
                        self.filter_attendee_ids = attendee_ids[0][2];
                    // liste d'identifiants
                    }else{
                        self.filter_attendee_ids = attendee_ids;
                        var idf, found;
                        // décocher les filtres qui ne sont pas dans attendee_ids
                        for (var k in self.all_filters) {
                            found = false;
                            idf = self.all_filters[k].value;
                            for (var l in attendee_ids) {
                                if (attendee_ids[l] == idf) {
                                    found = true;
                                    break;
                                }
                            }
                            if (!found) {
                                self.all_filters[k].is_checked = false;
                            }
                        };
                    }
                    dfd.resolve();
                });
            });

        return $.when(p);
    },
    set_res_horaires_data: function(res_ids=false, start=false, end=false, get_segments=false) {
        var self = this;
        this._super.apply(this,arguments);
        if (this.model == "of.planning.intervention" && this.show_creneau_dispo) {
            var dfd_creneaux_dispos = $.Deferred();
            var p_creneaux_dispos = dfd_creneaux_dispos.promise()
            res_ids = res_ids || self.now_filter_ids;
            start = start || self.range_start;
            end = moment(start).endOf(this.get_actual_mode() || "week")._d;

            var Planning = new Model(self.model);
            Planning.call('get_emp_horaires_info', [res_ids, start, end, get_segments, false, 'calendar'])
            .then(function (result) {
                if (isNullOrUndef(self.res_horaires_info)) {
                    self.res_horaires_info = result;
                }else{
                    for (var i=0; i<res_ids.length; i++) {
                        self.res_horaires_info[res_ids[i]] = result[res_ids[i]];
                    }
                }
                dfd_creneaux_dispos.resolve();
            });

            return $.when(p_creneaux_dispos).then(function() {

                // ajout des créneaux dispos
                self.events_dispo = [];
                var attendee_data, creneaux_dispo_jour, creneau_dispo, cmpt_id = -1;
                for (var k in self.now_filter_ids) {
                    var now_filter_id = self.now_filter_ids[k]
                    attendee_data = self.res_horaires_info[now_filter_id];
                    if (!isNullOrUndef(attendee_data)) {
                        for (var i=0; i<attendee_data.creneaux_dispo.length; i++) {
                            creneaux_dispo_jour = attendee_data.creneaux_dispo[i];
                            for (var j=0; j<creneaux_dispo_jour.length; j++) {
                                creneau_dispo = creneaux_dispo_jour[j];
                                creneau_dispo["calendar_name"] = "Dispo";
                                creneau_dispo["color_filter_id"] = now_filter_id;
                                creneau_dispo["employee_ids"] = [now_filter_id];
                                creneau_dispo["id"] = cmpt_id;
                                creneau_dispo["of_color_bg"] = "#FFFFFF";
                                creneau_dispo["of_color_ft"] = "#000000";
                                creneau_dispo["state"] = "Dispo";
                                creneau_dispo["state_int"] = 0;
                                creneau_dispo["virtuel"] = true;
                                self.events_dispo.push(creneau_dispo)
                                cmpt_id--;
                            }
                        }
                    }
                }

                return $.when();
            });
        }
        return $.when();
    },
    set_events_feries: function(start) {
        if (this.model != "of.planning.intervention") {
            return this._super.apply(this,arguments);
        }
        var self = this;
        this._super.apply(this,arguments);
        var end = moment(start).endOf(this.get_actual_mode() || "week")._d;
        var Company = new Model("res.company");

        var dfd_jours_feries = $.Deferred();
        var p_jours_feries = dfd_jours_feries.promise()
        Company.call('get_jours_feries', [start, end])
        .then(function (result) {
            if (result) {
                self.jours_feries = result;
            }

            dfd_jours_feries.resolve();
        });
        return $.when(p_jours_feries).then(function() {
            // ajout des créneaux de jours fériés
            self.events_feries = [];
            var cmpt_id = -10000;
            for (var kj in self.jours_feries) {
                var creneau_ferie = {
                    "id": cmpt_id,
                    "of_color_bg": "#FFFFFF",
                    "of_color_ft": "#000000",
                    "state": "Férié",
                    "state_int": 0,
                    "calendar_name": "Férié: " + self.jours_feries[kj],
                    "employee_ids": [],
                    "color_filter_id": 0,
                    "date_prompt": kj,
                    "date_deadline_prompt": kj,
                    "heure_debut": 0.0,
                    "heure_fin": 23.99,
                    "lieu_debut": false,
                    "lieu_fin": false,
                    "duree": 23.99,
                    "creneaux_reels": [(0.0, 23,99)],
                    "secteur_id": false,
                    "secteur_str": "",
                    "display_secteur": false,
                    "warning_horaires": false,
                    "ferie": true,
                    "virtuel": true,
                };
                creneau_ferie[self.all_day] = true
                for (var k in self.now_filter_ids) {
                    creneau_ferie["employee_ids"].push(k);
                }
                self.events_feries.push(creneau_ferie)
                cmpt_id--;
            }
            return $.when();
        });
    },
    /**
     *  Gestionnaire pour le clique sur un mode de planning
     */
    on_attendee_mode_clicked: function(ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        this.attendee_mode = ev.currentTarget.id.substring(14);
        this.attendee_mode_name = ATTENDEE_MODES[this.attendee_mode];
        // actualiser l'attendee_mode du view_manager
        this.view_manager.attendee_mode = this.attendee_mode

        var ir_values_model = new Model("ir.values");
        ir_values_model.call("set_default", ["of.intervention.settings", "attendee_mode", this.attendee_mode, false]);
        this.$buttons.find("#now_attendee_mode_name").text(this.attendee_mode_name);
        this.apply_extra_filters();
    },
    reload_extra_buttons: function () {
        var self = this;
        var ir_values_model = new Model("ir.values");
        var attendee_mode_def = ir_values_model.call("get_default",
                                                     ["of.intervention.settings", "attendee_mode", false]);

        return $.when(attendee_mode_def)
        .then(function(attendee_mode) {
            self.attendee_mode = attendee_mode;
            self.attendee_mode_name = ATTENDEE_MODES[self.attendee_mode];
            self.$buttons.find("#now_attendee_mode_name").text(self.attendee_mode_name);
            self.apply_extra_filters();
            return $.when();
        })
    },
    /**
     *  Méthode pour appliquer le filtrage par société et mode de planning
     *  Relance une recherche (qui lancera un re-rendu des filtres de droite)
     */
    apply_extra_filters: function() {
        if (this.model == 'of.planning.intervention'){
            this.now_filter_ids = []
            for (var i in this.all_filters) {
                this.all_filters[i].is_visible = false;

                if ((this.attendee_mode == "tech" && this.all_filters[i].est_intervenant)
                        || (this.attendee_mode == "com" && this.all_filters[i].est_commercial)
                        || (this.attendee_mode == "comtech"
                            && (this.all_filters[i].est_intervenant || this.all_filters[i].est_commercial))) {
                    this.now_filter_ids.push(this.all_filters[i].value);
                    this.all_filters[i].is_visible = true;
                }
            }
        }
        this.$calendar.fullCalendar('refetchEvents');
        $(':focus').blur();
    },
    event_data_transform: function(evt) {
        var r = this._super.apply(this,arguments);
        if (!evt.virtuel && this.model == 'of.planning.intervention') {
            evt.secteur_name = evt.secteur_id && evt.secteur_id[1] || false;
            // formatage des heures pour affichage dans tooltip
            var descript_ft = {type: "float_time"};
            var heures = Math.trunc(evt.duree);
            var minutes = (evt.duree - heures) * 60;
            if (!heures) {
                r.duree_str = minutes + "min";  // exple: 45min
            }else if (!minutes) {
                r.duree_str = heures + "h"  // exple: 2h
            }else{
                r.duree_str = formats.format_value(evt.duree,descript_ft).replace(":", "h");
                if (r.duree_str[0] == "0") {
                    r.duree_str = r.duree_str.substring(1);  // exple: 2h45
                }
            }
            evt.r = r;
        }
        return r
    },
    /**
     *  Redéfinition totale
     *  Simplement hériter cette méthode fonctionne mal. les boutons se retrouvent au mauvais endroit
     *  peut-être dû à l'héritage du template qweb qui rend l'action un tout petit peut plus lente + asynchronicité
     *  pourrait être FIX en ajoutant un template 'extra_buttons' plutôt que d'hériter 'CalendarView.buttons' peut-être
     */
    render_buttons: function($node) {
        var self = this;
        this.$buttons = $(QWeb.render("CalendarView.buttons", {'widget': this}));
        this.$buttons.on('click', 'button.o_calendar_button_new', function () {
            self.dataset.index = null;
            self.do_switch_view('form');
        });

        var bindCalendarButton = function(selector, arg1, arg2) {
            self.$buttons.on('click', selector, _.bind(self.$calendar.fullCalendar, self.$calendar, arg1, arg2));
        };
        bindCalendarButton('.o_calendar_button_prev', 'prev');
        bindCalendarButton('.o_calendar_button_today', 'today');
        bindCalendarButton('.o_calendar_button_next', 'next');
        bindCalendarButton('.o_calendar_button_day', 'changeView', 'agendaDay');
        bindCalendarButton('.o_calendar_button_week', 'changeView', 'agendaWeek');
        bindCalendarButton('.o_calendar_button_month', 'changeView', 'month');

        this.$buttons.find('.o_calendar_button_' + this.mode).addClass('active');
        this.$buttons.find(".of_attendee_mode_filter").click(self.proxy(self.on_attendee_mode_clicked));
        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            $('.o_cp_buttons').append(this.$buttons);
        }
    },
    do_push_state: function(state) {
        if (this.getParent() && this.getParent().do_push_state) {
            this.getParent().do_push_state(state);
            // l'attendee mode a changé depuis l'intialisation (changement de vue après avoir changé l'attendee_mode)
            // il faut recharger le bouton de filtrage supplémentaire
            if (this.view_inited && this.view_manager.attendee_mode != this.attendee_mode) {
                this.reload_extra_buttons();
            }

        }
    },
});
});
