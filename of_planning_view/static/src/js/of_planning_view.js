odoo.define('of_planning_view.PlanningView', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var Model = require('web.DataModel');
var View = require('web.View');
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');
var QWeb = require('web.QWeb');
var formats = require('web.formats');
var time = require('web.time');
var local_storage = require('web.local_storage');

var CompoundDomain = data.CompoundDomain;

var _t = core._t;
var _lt = core._lt;
var qweb = core.qweb;

var MODE_COLUMN_NBS = {
    "day": 1,
    "week": 7,
    "month": 7,
};

var ATTENDEE_MODES = {
    "tech": "Technique",
    "com": "Commercial",
    "comtech": "Technique & Commercial",
};

function hh_mm_to_float(hh_mm) {
    var heures = parseFloat(hh_mm.substring(0,2));
    var minutes = parseFloat(hh_mm.substring(3,5));
    return heures + (minutes / 60);
}

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
};

function hexToRgb(hex, mod) {
  var parsed = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  var result = parsed ? {
    r: parseInt(parsed[1], 16),
    g: parseInt(parsed[2], 16),
    b: parseInt(parsed[3], 16)
  } : null;
  if (!isNullOrUndef(mod) && !isNullOrUndef(parsed)) {
    result["r"] = mod < 0 ? Math.max(0, result["r"] + mod) : Math.min(255, result["r"] + mod);
    result["g"] = mod < 0 ? Math.max(0, result["g"] + mod) : Math.min(255, result["g"] + mod);
    result["b"] = mod < 0 ? Math.max(0, result["b"] + mod) : Math.min(255, result["b"] + mod);
  }
  return result;
}

var PlanningView = View.extend({
    template: 'PlanningView',
    display_name: _lt('Planning'),
    icon: 'fa fa-sliders',
    searchview_hidden: true,
    view_type: "planning",
    _model: null,
    events: {
        'click .of_planning_sidebar_toggler': 'toggle_full_width',
    },
    custom_events: {
        'all_rows_rendered': 'on_all_rows_rendered',
        'planning_record_open': 'open_record',
        'reload_events': 'on_reload_events',
    },
    /**
     *  Initialise la Vue
     */
    init: function (parent, dataset, view_id, options) {
        this._super.apply(this, arguments);
        var attrs = this.fields_view.arch.attrs;
        // attrributs date_start et resource obligatoires
        if (!attrs.date_start) {
            throw new Error(_t("Planning view has not defined 'date_start' attribute."));
        }
        if (!attrs.resource) {
            throw new Error(_t("Planning view has not defined 'resource' attribute."));
        }
        // retirer les search_default du context
        for (var k in this.dataset.context) {
            if (k.indexOf("search_default") != -1) {
                delete this.dataset.context[k];
            }
        }
        // de synchroniser le dataset des autre vues du modèle pour ne pas partager les filtres de recherche
        // en passant de la vue calendar à la vue planning par exemple
        this.dataset = new data.DataSetSearch(this.ViewManager.action_manager, 'of.planning.intervention', this.dataset.context, [])
        this.view_manager = this.getParent();
        this.fields = this.fields_view.fields;
        this.fields_keys = _.keys(this.fields_view.fields);
        this.name = this.fields_view.name || attrs.string;
        this.rows = []; // liste des lignes

        // true or 1 if we want to use multiple colors
        this.color_multiple = !isNullOrUndef(attrs.color_multiple) && _.str.toBool(attrs.color_multiple);
        this.resource = attrs.resource;  // nom du champ de ressource du modèle
        this.color_ft = attrs.color_ft;  // nom du champ de couleur de texte
        this.color_bg = attrs.color_bg;  // nom du champ de couleur de fond
        this.date_start = attrs.date_start;  // nom du champ de début d'évènement
        this.date_delay = attrs.date_delay;  // nom du champ de durée d'évènement
        this.date_stop = attrs.date_stop;  // nom du champ de fin d'évènement
        this.all_day = attrs.all_day;  // nom du champ de journée entière

        this.mode = attrs.mode || options.mode || "week";  // Seulement 'week' est implémenté pour le moment
        this.column_nb = MODE_COLUMN_NBS[this.mode];
        this.range_start = moment().startOf(this.mode)._d;  // borne de début de recherche
        this.range_stop = moment().endOf(this.mode)._d;  // borne de fin de recherche
        this.set_columns();  // initialiser les colonnes

        this.shown = $.Deferred();  // Deferred pour déclencher l'initialisation du tableau

        // de part l'asynchronicité, la première recherche est fait avant l'initialisation de la table
        // on lance donc 2 fois la première recherche avec un peu d'intervalle
        this.first_search_done = false;
        // debounce des handlers de click pour éviter le multiclick
        this.on_today_clicked = _.debounce(this.on_today_clicked, 300, true);
        this.on_next_clicked = _.debounce(this.on_next_clicked, 300, true);
        this.on_prev_clicked = _.debounce(this.on_prev_clicked, 300, true);
        this.on_attendee_mode_clicked = _.debounce(this.on_attendee_mode_clicked, 300, true);
    },
    /**
     *  Appel des fonction asynchrones qui doivent être terminées avant le lancement de la vue
     */
     willStart: function () {
        var self = this;
        var write_def = this.dataset.call("check_access_rights", ["write", false]);  // vérifier droits d'écriture
        var create_def = this.dataset.call("check_access_rights", ["create", false]);  // vérifier droits de lecture
        var rendered_prom = this.$el.html(qweb.render(this.template, this)).promise();
        // récupérer les employés à ne pas montrer en vue planning
        var excluded_ids_def = new Model("ir.values").call(
            "get_default", ["of.intervention.settings", "planningview_employee_exclu_ids"]);
        var intervenants_ids_def = new Model("hr.employee").query(['id'])
            .filter([
                '|',
                ['of_est_intervenant', '=', true],
                ['of_est_commercial', '=', true]]) // seulement les intervenants / commerciaux
            .order_by(['sequence'])
            .all();  // récupérer tous les employés qui sont des intervenants
        var ir_values_model = new Model("ir.values");
        // doit-on laisser la taille des events auto?
        var mode_calendar_def = ir_values_model.call("get_default",
                                                    ["of.intervention.settings", "planningview_calendar"]);
        // combien de pixel / heure ?
        var duree_to_px_def = ir_values_model.call("get_default",
                                                   ["of.intervention.settings", "planningview_h2px"]);
        var heure_min_def = ir_values_model.call("get_default",
                                                 ["of.intervention.settings", "planningview_min_time"]);
        var heure_max_def = ir_values_model.call("get_default",
                                                 ["of.intervention.settings", "planningview_max_time"]);
        var time_line_def = ir_values_model.call("get_default",
                                                 ["of.intervention.settings", "planningview_time_line"]);
        // récupérer l'info pour savoir si afficher le planning Tech, Com, ou les deux
        var attendee_mode_def = ir_values_model.call("get_default",
                                                     ["of.intervention.settings", "attendee_mode", false]);
        // récupérer les info pour l'affichage du bouton de filtrage par société
        var company_filters_def = new Model("res.company").call("get_company_filter_ids", []);
        var company_filter_def = ir_values_model.call("get_default",
                                                      ["of.intervention.settings", "company_filter_id", false]);
        // de quelle couleur afficher les jours fériés?
        var color_jours_feries_def = ir_values_model.call(
            "get_default", ["of.intervention.settings", "color_jours_feries"]);
        // masquer les pictos de recherche et d'assignation de secteur?
        var ignorer_jours_feries_def = ir_values_model.call(
            "get_default", ["of.intervention.settings", "ignorer_jours_feries"]);
        // initialiser les couleurs des créneaux dispo et leur durée minimale
        var creneaux_dispo_data_def = self.set_creneaux_dispo_data();

        return $.when(
            write_def, create_def, excluded_ids_def, intervenants_ids_def, mode_calendar_def, duree_to_px_def,
            heure_min_def, heure_max_def, time_line_def, attendee_mode_def, company_filters_def, company_filter_def,
            color_jours_feries_def, ignorer_jours_feries_def, rendered_prom, creneaux_dispo_data_def, this._super()
        ).then(
            function (write, create, excluded, emp_ids, mode_calendar, duree_to_px, min_time, max_time, time_line,
            attendee_mode, company_filters, now_company_id, color_jours_feries, ignorer_jours_feries) {
                self.write_right = write;
                self.create_right = create;
                // affecter le mode de planning (com, tech ou comtech)
                self.attendee_mode = attendee_mode || "comtech";
                self.attendee_mode_name = ATTENDEE_MODES[self.attendee_mode];
                // initialiser l'attendee_mode du view_manager
                self.view_manager.attendee_mode = self.attendee_mode
                // retirer les intervenants à ne pas montrer en vue planning
                var excluded_ids = [], to_show_ids = [];
                if (!!excluded) {
                    excluded_ids = excluded[0][2]  // [(6, 0, [ids_list])]
                }
                for (var i=0; i<emp_ids.length; i++) {
                    if (!excluded_ids.includes(emp_ids[i].id)) {
                        to_show_ids.push(emp_ids[i].id)
                    }
                }
                self.view_res_ids = to_show_ids;
                // initialiser les filtres grâce à la liste des intervenants à montrer en vue planning
                var all_filters_def = self._set_all_custom_colors();

                self.mode_calendar = mode_calendar;
                self.duree_to_px = duree_to_px;
                self.min_time = min_time;
                self.max_time = max_time;
                if (time_line) {
                    time_line = "[" + time_line + "]";
                }else{
                    time_line = "[]";
                }
                self.time_line = JSON.parse(time_line)

                self.company_filters = company_filters;
                self.now_company_id = now_company_id || 0;

                self.company_ids_indexes = {}
                var company_fil,current_comp_j;
                self.company_filters.push({id: 0, name: "Toutes"})
                for (var j=0; j<self.company_filters.length; j++) {
                    company_fil = self.company_filters[j];
                    self.company_ids_indexes[company_fil.id] = j;
                    if (company_fil.id == self.now_company_id) {
                        self.now_company_name = company_fil.name;
                    }
                    if (company_fil['current']) {
                        current_comp_j = j;
                    }
                }
                if (isNullOrUndef(self.now_company_name)){
                    self.now_company_name = self.company_filters[current_comp_j].name;
                    self.now_company_id = self.company_filters[current_comp_j].id;
                }

                self.jours_feries_opt = {
                    'ignorer_jours_feries': ignorer_jours_feries,
                    'color_jours_feries': color_jours_feries,
                }

                return $.when(all_filters_def);
        });
    },
    do_push_state: function(state) {
        if (this.getParent() && this.getParent().do_push_state) {
            this.getParent().do_push_state(state);
            // l'attendee mode a changé depuis l'intialisation (changement de vue après avoir changé l'attendee_mode)
            // il faut recharger le bouton de filtrage supplémentaire
            if (this.attendee_mode != this.view_manager.attendee_mode) {
                this.reload_extra_buttons();
            }
        }
    },
    /**
     *  initialise les couleurs des créneaux dispos.
     *  Ainsi que la durée minimale pour qu'un créneau libre soit considéré comme disponible
     */
    set_creneaux_dispo_data: function () {
        var self = this;
        var ir_values_model = new Model("ir.values")
        var bg_def = ir_values_model.call("get_default", ["of.intervention.settings", "color_bg_creneaux_dispo"]);
        var ft_def = ir_values_model.call("get_default", ["of.intervention.settings", "color_ft_creneaux_dispo"]);
        var dureemin_def = ir_values_model.call("get_default", ["of.intervention.settings", "duree_min_creneaux_dispo"]);
        return $.when(bg_def, ft_def, dureemin_def)
        .then(function (bg, ft, duree) {
            self.creneaux_dispo = {
                'color_bg': bg,
                'color_ft': ft,
                'duree_min': duree,
            }
            return $.when();
        });
    },
    /**
     *  appelé par PlanningView.willStart
     *  initialise this.all_filters en conservant la dernière sélection
     */
    _set_all_custom_colors: function() {
        var self = this;
        var ids = _.reject(self.all_filters,function(filter){ return filter.id == 'undefined'; });

        var dfd = $.Deferred();
        var p = dfd.promise();
        var model_name = self.fields[self.resource].relation;
        var Attendees = new Model(model_name);
        self.actual_res_ids = []

        // récupérer les infos des employés pour générer les filtres de droite
        Attendees.query(['id', self.color_ft, self.color_bg, 'name', 'sequence', 'of_est_intervenant',
                         'of_est_commercial', 'company_id'])
            .filter([['id', 'in', self.view_res_ids || []]]) // id
            .order_by(['sequence'])
            .all()
            .then(function (attendees){
                self.all_filters = new Array(attendees.length);  // Array pour conserver l'ordre
                // dictionnaire de la forme {id: index_filtre}
                // pour accéder facilement à l'indexe du filtre à partir de l'id de l'attendee
                self.res_ids_indexes = {}
                var a, filter_item;
                var all_company_ids = _.pluck(self.company_filters, 'id');
                for (var i=0; i<attendees.length; i++) {
                    a = attendees[i];
                    filter_item = {
                        label: a['name'],
                        color_bg: a[self.color_bg],
                        color_ft: a[self.color_ft],
                        est_intervenant: a['of_est_intervenant'],
                        est_commercial: a['of_est_commercial'],
                        company_id: a['company_id'],
                        value: a['id'],
                        input_id: a['id'] + "_input",
                        is_checked: true,
                        is_visible: false,
                        sequence: a['sequence'],
                    }
                    // ne montrer que les filtres (à droite) qui passent le filtrage par société et type de planning
                    if (self.attendee_mode == 'tech' && a['of_est_intervenant'] ||
                      self.attendee_mode == 'com' && a['of_est_commercial'] || self.attendee_mode == 'comtech') {
                        if (!a['company_id']
                          || !self.now_company_id && _.contains(all_company_ids, a['company_id'][0])
                          || a['company_id'][0] == self.now_company_id) {
                            self.actual_res_ids.push(a['id']);
                            filter_item.is_visible = true;
                        }
                    }
                    self.all_filters[i] = filter_item;
                    self.res_ids_indexes[a['id']] = i;
                };
                var ir_values_model = new Model("ir.values");
                // récupérer la sélection (coché/décoché) des filtres de la dernière utilisation de la vue planning
                // par l'utilisateur. Les filtres cochés sont dans la variable filter_attendee_ids
                ir_values_model.call("get_default",
                                     ["of.intervention.settings", "of_filter_attendee_ids", false])
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
    /**
     *  Appelé à la fin de willStart quand toutes les fonctions asynchrones sont résolues
     */
    start: function () {
        // raccourcis jquery
        this.$sidebar_container = this.$(".of_planning_sidebar_container");  // Panneau latéral droit
        this.$table_container = this.$(".of_planning_table_container");  // Contenu de la vue
        this.$el.addClass(this.fields_view.arch.attrs.class);
        this.shown.done(this.init_table.bind(this));  // initialiser la table quand la vue est chargée
        return this._super();
    },
    /**
     *  Appelé quand la vue planning doit être affichée.
     */
    do_show: function() {
        this.do_push_state({});
        this.shown.resolve();
        return this._super();
    },
    /**
     *  Initialise la Table et le panneau latéral droit, puis lance do_search
     */
    init_table: function() {
        var self = this;
        this.table = new PlanningView.Table(this);
        var defs = [];
        if (!this.sidebar) {  // n'a pas déjà été initialisé
            this.sidebar = new PlanningView.Sidebar(this);
            defs.push(this.sidebar.appendTo(this.$sidebar_container));

            this.$small_calendar = this.$(".of_planning_calendar_mini");
            this.$small_calendar.datepicker({
                onSelect: this.calendarMiniChanged(this),
                dayNamesMin : moment.weekdaysShort(),
                monthNames: moment.monthsShort(),
                firstDay: moment()._locale._week.dow,
            });

            // Add show/hide button and possibly hide the sidebar
            this.$sidebar_container.append($('<i>').addClass('of_planning_sidebar_toggler fa'));
            var lateral_droit = new Model("ir.values").call("get_default",
                                                            ["of.intervention.settings", "lateral_droit", false])
            .then(function (res) {
                self.toggle_sidebar(res);
            });

        }
        return $.when.apply($, defs)
        .then(function () {
            self.table_inited = true;
            self.do_search(this.domain,this.context,this.group_by);
        });
    },
    /**
     *  Handler pour le click sur un élément du mini-calendrier
     */
    calendarMiniChanged: function (view) {
        return function(datum,obj) {
            var curMode = view.mode;
            var curDate = new Date(obj.currentYear , obj.currentMonth, obj.currentDay);

            if (curMode == "week") {
                if (curDate <= view.range_stop && curDate >= view.range_start) {  // day of same week
                    //console.log("that doesn't do anything...")
                }else{
                    view.range_start = moment(curDate).startOf("week")._d;
                    view.range_stop = moment(curDate).endOf("week")._d;
                    view.do_search(view.domain, view.context, view.group_by);
                }
            }
        };
    },
    /**
     *  Handler pour le click sur la petite croix / le chevron du panneau latéral droit
     */
    toggle_full_width: function () {
        var self = this;
        var ir_value_model = new Model("ir.values")
        ir_value_model.call("get_default", ["of.intervention.settings", "lateral_droit", false])
        .then(function (lateral_droit) {
            lateral_droit = !lateral_droit;
            ir_value_model.call("set_default", ["of.intervention.settings", "lateral_droit", lateral_droit, false]);
            self.toggle_sidebar(lateral_droit);
        });
    },
    /**
     *  Appelé par init_table et toggle_full_width. Montre / Cache le panneau latéral droit
     */
    toggle_sidebar: function (display) {
        this.sidebar.do_toggle(display);
        this.$('.of_planning_sidebar_toggler')
            .toggleClass('fa-close', display)
            .toggleClass('fa-chevron-left', !display)
            .attr('title', display ? _('Close Sidebar') : _('Open Sidebar'));
        this.$sidebar_container.toggleClass('of_sidebar_hidden', !display);
    },
    /**
     *  appelé une première fois après l'initialisation de la vue, puis après l'initialisation de ses composants.
     *  appelé ensuite par click sur les boutons en haut à gauche ou sur le mini-calendrier.
     *  lance (ou non si les composant ne sont pas initialisés) la recherche  d'évènements.
     */
    do_search: function (domain, context, group_by) {
        var self = this;
        var ir_values_model = new Model('ir.values');
        this.domain = [];
        this.context = context;
        this.group_by = group_by;

        // ne pas lancer la recherche si l'attendee_mode en mémoire est différent de l'attendee_mode du view_manager
        if (self.table_inited && self.first_search_done && this.attendee_mode == this.view_manager.attendee_mode) {
            self._do_search(self.domain, self.context, self.group_by);
        }else{
            self.first_search_done = true;
            console.log('do_search not done, planning view not inited');
        }
    },
    /**
     *  Appelé par do_search. Créé les lignes de ressource et y affecte les évènements. Lance le rendu de la Table
     */
    _do_search: function(domain, context, group_by) {
        var self = this;
        if (! self.all_filters) {  // foolproofing
            self.all_filters = [];
        }
        if (isNullOrUndef(context)) {
            context = {};
        }
        context['virtual_id'] = true;
        self.rows = new Array(self.view_res_ids.length);
        // dictionnaire de la forme {id: index_row}
        // pour accéder facilement à l'indexe du filtre à partir de l'id de l'attendee
        self.rows_ids_indexes = {}
        var row_options, emp_id;
        // Création des lignes
        for (var i in self.view_res_ids) {
            emp_id = self.view_res_ids[i];
            if (!self.actual_res_ids.includes(emp_id)){
                continue;
            }

            row_options = {
                "res_id": emp_id,
                "auto_render": false,
            }
            self.rows_ids_indexes[emp_id] = i

            self.rows[i] = new PlanningView.Row(self.table,self,[],row_options);
            self.rows[i].head_column = self.all_filters[self.res_ids_indexes[emp_id]].label;
        }
        self.col_offset_today = null;
        // le jour d'aujourd'hui est présent dans la recherche
        // on stocke son col_offset pour pouvoir l'afficher différemment (plus foncé)
        if (moment(self.range_start) <= moment() && moment() <= moment(self.range_stop)) {
            self.col_offset_today = moment().startOf('day').diff(moment(self.range_start), 'days');
        }
        // générer le domain effectif de la vue planning (qui n'a pas de vue recherche)
        // actualise la liste des jours fériés au passage
        var temp = self.get_range_domain([],this.range_start,this.range_stop).then(function () {
            // rechercher les évènements en bdd
            // initialiser les segments horaires, les fillerbars, les créneaux dispos et les couleurs des attendees
            var prom = self.set_res_horaires_data(self.fields_keys);
            $.when(prom).then(function () {
                // adapter les entêtes de colonnes aux nouvelles bornes de recherche
                self.set_columns();
                var event, planning_record, day_span, col_offset_start, col_offset_stop, record_options,
                    event_res_ids, res_id, row_index, start_local, stop_local;
                for (var event_key in self.events) {
                    event = self.events[event_key];
                    event_res_ids = event[self.resource];
                    // calculer les heures locales pour placer les events dans les bonnes colonnes
                    start_local = moment.utc(event[self.date_start]).local()
                    stop_local = moment.utc(event[self.date_stop]).local()
                    // combien de jours?
                    day_span = stop_local.startOf('day').diff(start_local.startOf('day'), 'days')+1;
                    // l'enregistrement sera ajouté à toutes les colonnes entre col_offset_start et col_offset_stop
                    col_offset_start = start_local.startOf('day').diff(moment(self.range_start), 'days');
                    if (day_span > 1) {
                        col_offset_stop = stop_local.startOf('day').diff(moment(self.range_start), 'days');
                    }else{
                        col_offset_stop = undefined;
                    }

                    record_options = {
                        "col_offset_start": col_offset_start,
                        "col_offset_stop": col_offset_stop,
                        "day_span": day_span,
                    }
                    // ajouter l'évènement aux lignes de ressource concernées
                    for (var j in event_res_ids) {
                        res_id = event_res_ids[j];
                        row_index = self.rows_ids_indexes[res_id]
                        // Ajouter l'évènement seulement aux lignes à afficher
                        if (_.contains(self.actual_res_ids, res_id)) {
                            planning_record = new PlanningRecord(self.rows[row_index],self,event,record_options);
                            self.rows[row_index]["records_to_add"].push(planning_record);
                        }
                    }
                }

                if (self.sidebar) {
                    // rendre les filtres des attendee en appliquant les couleurs
                    self.sidebar.reso_filter.render();
                    // ne pas montrer les lignes de ressources pour les filtres décochés
                    for (var row_index in self.rows) {
                        var key_num = Number(self.rows[row_index].res_id);
                        if (self.all_filters[self.res_ids_indexes[key_num]].is_checked) {
                            self.rows[row_index].hidden = false;
                        }else{
                            self.rows[row_index].hidden = true;
                        }
                    }
                }
                var bg_rgb, ft_rgb, rgb_today, key;
                // Affecter les valeurs reçues par set_res_horaires_data aux lignes
                for (var row_index in self.rows) {
                    key = self.rows[row_index].res_id;
                    self.rows[row_index].segments_horaires = self.res_horaires_info[key]['segments'];
                    self.rows[row_index].col_offset_to_segment = self.res_horaires_info[key]['col_offset_to_segment'];
                    self.rows[row_index].fillerbars = self.res_horaires_info[key]['fillerbars'];
                    self.rows[row_index].creneaux_dispo = self.res_horaires_info[key]['creneaux_dispo'];
                    self.rows[row_index].color_bg = self.res_horaires_info[key]['color_bg'];
                    self.rows[row_index].color_ft = self.res_horaires_info[key]['color_ft'];
                    self.rows[row_index].tz = self.res_horaires_info[key]['tz'];
                    self.rows[row_index].tz_offset = self.res_horaires_info[key]['tz_offset'];
                    bg_rgb = hexToRgb(self.res_horaires_info[key]['color_bg']);
                    self.rows[row_index].color_bg_rgba = "rgba(" + bg_rgb.r + "," + bg_rgb.g + "," + bg_rgb.b +
                        ",0.3);";
                    ft_rgb = hexToRgb(self.res_horaires_info[key]['color_ft']);
                    self.rows[row_index].color_ft_rgba = "rgba(" + ft_rgb.r + "," + ft_rgb.g + "," + ft_rgb.b +
                        ",0.8);";
                    self.rows[row_index].col_offset_today = isNullOrUndef(self.col_offset_today) ?
                        -1 : self.col_offset_today;
                    if (self.rows[row_index].col_offset_today != -1) {
                        rgb_today = hexToRgb(self.res_horaires_info[key]['color_bg'], -30);
                        self.rows[row_index].color_bg_rgba_today = "rgba(" + rgb_today.r + "," + rgb_today.g + "," +
                            rgb_today.b + ",0.4);";
                    }
                }

                self.table.rows = self.rows;
                self.render_table();
            });
        });
    },
    /**
     *  Appelé par _do_search.
     *  Initialise les segments horaires, les fillerbars, les créneaux dispos et les couleurs des attendees
     */
    set_res_horaires_data: function(return_fields=[], res_ids=false, start=false, end=false, segments=false) {
        var self = this;
        var dfd = $.Deferred();
        var p = dfd.promise()
        res_ids = res_ids || self.actual_res_ids;
        start = start || self.range_start;
        end = end || self.range_stop;

        var Planning = new Model(self.model);
        Planning.call(
            'get_display_data', [res_ids, start, end, segments, !self.mode_calendar, 'planning', return_fields])
        .then(function (result) {
            if (isNullOrUndef(self.res_horaires_info)) {
                self.res_horaires_info = {};
            }
                for (var i=0; i<res_ids.length; i++) {
                    self.res_horaires_info[res_ids[i]] = result[res_ids[i]];
                }
                self.events = result['interventions']


            dfd.resolve();
        });
        return $.when(p);
    },
    /**
     *  Rends la Table puis chacune de ses lignes
     */
    render_table: function() {
        var self = this;
        var rendered_prom = this.$(".of_planning_table")
            .html(qweb.render("PlanningView.table", {"table": this.table})).appendTo(self.$table_container).promise();

        return $.when(rendered_prom)
            .then(function () {  // rendre les lignes
                _.each(self.rows, function(row) {
                    if (!isNullOrUndef(row)) {
                        row.render();
                    }
                });
            });
    },
    /**
     * Render the buttons according to the PlanningView.buttons template and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the ListView inserts them into this.options.$buttons
     * or into a div of its template
     */
    render_buttons: function($node) {
        var self = this;
        this.$buttons = $(qweb.render("PlanningView.buttons", {'widget': this}));
        this.$buttons.on('click', 'button.of_planning_button_new', function () {
            self.dataset.index = null;
            self.do_switch_view('form');
        });

        this.$buttons.find(".of_planning_button_prev").click(this.proxy(self.on_prev_clicked));
        this.$buttons.find(".of_planning_button_today").click(this.proxy(self.on_today_clicked));
        this.$buttons.find(".of_planning_button_next").click(this.proxy(self.on_next_clicked));
        // boutons de filtrage par société et type de planning
        this.$buttons.find(".of_company_filter").click(this.proxy(self.on_company_filter_clicked));
        this.$buttons.find(".of_attendee_mode_filter").click(this.proxy(self.on_attendee_mode_clicked));

        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            this.$('.of_planning_buttons').replaceWith(this.$buttons);
        }
    },
    /**
     *  Handler pour le click sur bouton "précédent" (flèche gauche). Lance do_search
     */
    on_prev_clicked: function (ev) {
        this.range_stop = moment(this.range_start).subtract(1, 'hours').endOf(this.mode)._d;
        this.range_start = moment(this.range_start).subtract(1, 'hours').startOf(this.mode)._d;
        this.$small_calendar.datepicker("setDate",moment(this.range_start).format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    /**
     *  Handler pour le click sur bouton "suivant" (flèche droite). Lance do_search
     */
    on_today_clicked: function(ev) {
        this.range_start = moment().startOf(this.mode)._d;
        this.range_stop = moment().endOf(this.mode)._d;
        this.$small_calendar.datepicker("setDate",moment().format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    /**
     *  Handler pour le click sur bouton "Aujourd'hui". Lance do_search
     */
    on_next_clicked: function (ev) {
        this.range_start = moment(this.range_stop).add(1, 'hours').startOf(this.mode)._d;
        this.range_stop = moment(this.range_stop).add(1, 'hours').endOf(this.mode)._d;
        this.$small_calendar.datepicker("setDate",moment(this.range_start).format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    /**
     *  Gestionnaire pour le clique sur un filtre de société
     */
    on_company_filter_clicked: function(ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        this.now_company_id = parseInt(ev.currentTarget.id.substring(15), 10);
        this.now_company_name = this.company_filters[this.company_ids_indexes[this.now_company_id]].name;

        var ir_values_model = new Model("ir.values");
        ir_values_model.call("set_default",
                             ["of.intervention.settings", "company_filter_id", this.now_company_id, false]);
        this.$buttons.find("#now_company_name").text(this.now_company_name);
        this.apply_extra_filters();
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
        this.actual_res_ids = [];
        var all_company_ids = _.pluck(this.company_filters, 'id');
        for (var i in this.all_filters) {
            this.all_filters[i].is_visible = false;

            if (!this.all_filters[i].company_id
                || !this.now_company_id && _.contains(all_company_ids, this.all_filters[i].company_id[0])
                || this.all_filters[i].company_id[0] == this.now_company_id) {
                if (this.attendee_mode == "tech" && this.all_filters[i].est_intervenant
                  || this.attendee_mode == "com" && this.all_filters[i].est_commercial
                  || this.attendee_mode == "comtech") {
                    this.actual_res_ids.push(this.all_filters[i].value);
                    this.all_filters[i].is_visible = true;
                }
            }
        }
        this.do_search(this.domain,this.context,this.group_by);
        $(':focus').blur();
    },

    /**
     *  Handles signal that all rows are rendered
     *  Applique les filtres d'affichage des informations sur les évènements
     *  Ajoute l'infobulle sur les créneaux dispo si au moins un évènement a ses dates forcées (of.planning.intervention)
     */
    on_all_rows_rendered: function() {
        if (this.sidebar) {
            if (this.sidebar.info_filter.rendered) {
                this.sidebar.info_filter.apply_filters();
            }else{
                this.sidebar.info_filter.render();
            }
        }
        var tooltip_options = {
                        delay: { show: 501, hide: 0 },
                        title: "Au moins une intervention a ses horaires forcés aujourd'hui.\n" +
                               "Par conséquent, le temps disponible de cet intervenant pour ce créneau est peut-être erroné.",
                    }
        $(".of_warning_horaires").tooltip(tooltip_options)
    },
    /**
     *  Handler pour le signal de recharger les évènements. Lance _do_search
     *  En cas de lenteur on pourra tenter de réparer on_reload_column
     */
    on_reload_events: function () {
        this._do_search(this.domain, this.context, this.group_by);
    },
    /**
     *  Doesn't work as of now. the difficulty is for multiple day and multiple employee events
     * /
    on_reload_column: function (res_id, column, columns_done=[]) {
        console.log("on_reload_column", res_id, column);
        var self = this;
        var date_column = moment(this.range_start).add(column, 'days')
        var date_fin = date_column.endOf('day')._d;
        date_column = date_column._d;
        var columns_todo = [];
        var event_domain = this.get_range_domain(this.domain || [], date_column, date_fin, [res_id]);
        this.rows[res_id].clear_column(column);
        this.dataset.read_slice(this.fields_keys, {offset: 0, domain: event_domain, context: self.context,
        }).done(function(events) {
            if (events.length >0) {

                var event, planning_record, day_span, col_offset_start, col_offset_stop, record_options, row_options, event_res_ids;
                for (var i=0; i<events.length; i++) {
                    event = events[i];
                    event_res_ids = event[self.resource];
                    // how many days?
                    day_span = moment(event[self.date_stop]).startOf('day').diff(moment(event[self.date_start]).startOf('day'), 'days')+1;
                    // the column index to insert the record
                    col_offset_start = moment(event[self.date_start]).startOf('day').diff(moment(self.range_start), 'days');
                    if (col_offset_start < 0) {
                       //console.log("TROP TOT")
                    }else if (col_offset_start >= self.column_nb) {
                       //console.log("TROP TARD");
                    }
                    if (day_span > 1) {  // multiple day record, we need to reload every column this record is in
                        col_offset_stop = moment(event[self.date_stop]).startOf('day').diff(moment(self.range_start), 'days');
                        /*for (var c=Math.max(0, col_offset_start); c < Math.min(self.column_nb, col_offset_stop + 1)) {
                            if (!_.contains(columns_done, c) && !_.contains(columns_todo, c) && c != column) {
                                columns_todo.push(c)
                            }
                        }* /
                        //col_offset_stop = Math.min(col_offset_stop,6);
                    }else{
                        col_offset_stop = undefined;
                    }

                    record_options = {
                        "col_offset_start": col_offset_start,
                        "col_offset_stop": col_offset_stop,
                        //"color_bg": event[self.color_bg] || "#7FFF00",
                        //"color_ft": event[self.color_ft] || "#0C0C0C",
                        "day_span": day_span,
                    }

                    //self.view_res_ids = _.union(self.view_res_ids, event_res_ids);
                    //for (var j in event_res_ids) {
                        //res_id = event_res_ids[j];
                        /*if (!self.all_filters[res_id]) {
                            filter_item = {
                                value: res_id,
                                input_id: res_id + "_input",
                                label: event[self.resource],
                                //color: self.get_color(key),
                                //avatar_model: (utils.toBoolElse(self.avatar_filter, true) ? self.avatar_filter : false ),
                                is_checked: true,
                            };
                            self.all_filters[res_id] = filter_item;
                        };
                        if (! _.contains(self.now_filter_ids, res_id)) {
                            self.now_filter_ids.push(res_id);
                        };
                        if (!self.rows[res_id]) {
                            row_options = {
                                "res_id": res_id,
                                //"head_column": "",
                                //"color_bg": event[self.color_bg] || "#7FFF00",
                                //"color_ft": event[self.color_ft] || "#0C0C0C",
                                "auto_render": false,
                            }
                            self.rows[res_id] = new PlanningView.Row(self.table,self,[],row_options);
                        }* /

                        planning_record = new PlanningRecord(self.rows[res_id],self,event,record_options);
                        self.rows[res_id]["records_to_add"].push(planning_record);
                    //}
                }
            }
            var prom = self.set_res_horaires_data([res_id], date_column, date_fin, self.res_horaires_info[res_id].segments_horaires);
            $.when(prom).then(function () {
                self.rows[res_id].fillerbars[column] = self.res_horaires_info[res_id]['fillerbars'][0];
                self.rows[res_id].creneaux_dispo[column] = self.res_horaires_info[res_id]['creneaux_dispo'][0];
                self.rows[res_id].render(column);
            });
        });
    },*/
    /**
     *  Ouvre la vue form d'un évènement
     */
    open_record: function (event, options) {
        var self = this;
        var additional_context = {};
        var action_id = "of_planning.action_of_planning_intervention_form"

        return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
                result.res_id = event.data.id;
                var options = {
                    'additional_context': pyeval.eval('context', additional_context),
                    'on_close': function () {self.trigger_up('reload_events')},
                };
                return self.ViewManager.action_manager.do_action(result,options);
            });
    },
    /**
     *  Init columns data based on mode. right now just 'week'
     */
    set_columns: function() {
        switch (this.mode) {
            case "week": return this.set_columns_week();
        };
    },
    set_columns_week: function() {
        this.head_column = {
            "text": "S" + moment(this.range_start).add(1, 'days').week(),
            "type": "resource_info",
        };
        var res = [];
        var jours = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."];
        var le_text, la_date, le_dict = {}, la_class;
        for (var i=0; i<this.column_nb; i++) {
            la_class = "of_planning_column_day"
            le_text = jours[i] + " " + moment(this.range_start).add(i, 'days').format('L');
            la_date = moment(this.range_start).add(i, 'days')._d;
            if (this.col_offset_today == i) la_class += " of_planning_column_today"
            le_dict = {
                "text": le_text,
                "date": la_date,
                "type": "date",
                "class": la_class,
            }
            res.push(le_dict);
        }
        this.columns = res;
        if (!isNullOrUndef(this.table)) {
            this.table.head_column = this.head_column;
            this.table.columns = this.columns;
        }
        return res;
    },
    /**
     * Construit un Domain pour filtrer par les champs de this.date_start et this.date_stop
     * entre les dates start et end.
     * pour les id de resource res_ids
     * actualise self.jours_feries
     */
    get_range_domain: function(domain, start, end, res_ids) {
        var self = this;
        var jours_feries_def = new Model("res.company").call("get_jours_feries", [start, end]);
        var format = time.datetime_to_str;
        res_ids = res_ids || this.actual_res_ids;
        var extend_domain = [[this.date_start, '<=', format(end)]];
        if (this.date_stop) {
            extend_domain.push([this.date_stop, '>=', format(start)]);
        } else if (!this.date_delay) {
            extend_domain.push([this.date_start, '>=', format(start)]);
        }
        extend_domain.push(['employee_ids', 'in', res_ids]);
        return $.when(jours_feries_def).then(function (jours_feries_dict) {
            self.jours_feries = jours_feries_dict
            self.event_domain = new CompoundDomain(domain, extend_domain)
            return $.when();
        })
    },
});


PlanningView.Table = Widget.extend({
    template: "PlanningView.table",
    custom_events: {
        'row_rendered': 'on_row_rendered',
    },
    init: function(parent, options) {
        this._super.apply(this, arguments);
        this.view = parent;
        this.columns = this.view.columns;
        this.head_column = this.view.head_column;
        this.rows = this.view.rows;
        this.appendTo(this.view.$table_container);
    },
    /**
     *  Surcharge de la fonctionne parente pour avoir la variable 'table' dans le template XML
     */
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(qweb.render(this.template, {table: this}).trim());
        } else {
            $el = this._make_descriptive();
        }
        this.replaceElement($el);
    },
    /**
     *  Handler pour le signal de rendu d'une ligne. Vérifie si toutes les lignes sont rendues et le signale
     */
    on_row_rendered: function() {
        if (this.check_all_rows_rendered()) {
            this.trigger_up("all_rows_rendered");
        }
    },
    /**
     *  Vérifie si toutes les lignes sont rendues
     */
    check_all_rows_rendered: function() {
        for (var i in this.rows) {
            if (!this.rows[i].rendered) {
                return false;
            }
        }
        return true;
    },
});


PlanningView.Row = Widget.extend({
    template: "PlanningView.row",
    tagName: 'tr',
    custom_events: {
        'record_added': 'on_record_added',
        'all_records_added': 'on_all_records_added',
    },
    init: function(parent, view, records, options) {
        var self = this;
        this._super.apply(this, arguments);
        this.options = options;
        this.res_id = options.res_id;
        this.id = "of_planning_row_" + this.res_id;
        this.hidden = options.hidden || false;
        this.table = view.table;
        this.view = view;
        this.fillerbar_color_dispo = view.creneaux_dispo.color_bg;
        this.model = new Model(this.view.fields[this.view.resource].relation);
        // initialisation des colonnes
        this.head_column = this.options.head_column;  // colonne avec le nom de la ressource
        this.column_nb = this.view.column_nb;
        this.columns = new Array(this.column_nb);
        for (var i=0; i<this.columns.length; i++) {
            this.columns[i] = [];
        }
        this.fillerbars = [];
        this.records_multiples = {};
        this.records_to_add = [];  // enregistrements à ajouter
        this.records_added = [];  // enregistrements ajoutés
        // sera résolu quand tous les enregistrements seront assignés à une ou plusieurs colonnes
        self.ready_to_render = $.Deferred();
    },
    /**
     *  col_index optionnel, garder undefined pour rendre toutes les colonnes
     */
    render: function (col_index, reload=false) {
        var self = this;

        var le_model = new Model("of.planning.intervention");
        var fillerbarzz = [];
        self.assing_records_to_columns();
        // attendre que tous les enregistrements soient assignés pour lancer le rendu
        $.when(self.ready_to_render).then(function(){  // pré-rendu
            var le_creneau, formatted_heure_record, formatted_heure_creneau;
            var descript_dt = {type: "datetime"};
            var descript_ft = {type: "float_time"};
            var options = {};
            if (!self.creneaux_dispo.length) {
                self.zero_horaire = true;
            }else{  // ajouter les créneaux dispos aux colonnes
                self.zero_horaire = false;
                if (!reload) {
                    var max_time = self.view.max_time, event, record;
                    for (var i=0; i<self.column_nb; i++) {  // parcourir les colonnes
                        options = {col_offset: i};
                        if (isNullOrUndef(col_index) || i==col_index) {
                            for (var j=0; j<self.creneaux_dispo[i].length; j++) {  // parcourir les créneaux dispos
                                le_creneau = new PlanningCreneauDispo(self, self.view, self.creneaux_dispo[i][j], options);
                                self.columns[i].push(le_creneau);
                                // définition de compareFunction ici car elle utilise la variable i
                                // contournement de l'argument compareFunction de la fonction sort de Array
                                // qui n'accepte que 2 paramètre
                                function compareFunction(recA, recB) {
                                    var heure_debut_a = recA.heure_debut,
                                        heure_debut_b = recB.heure_debut;
                                    if (!isNullOrUndef(recA.hours_cols)) {  // si recA est sur plusieurs jours
                                        heure_debut_a = recA.hours_cols[i].heure_debut;
                                    }
                                    if (!isNullOrUndef(recB.hours_cols)) {  // si recB est sur plusieurs jours
                                        heure_debut_b = recB.hours_cols[i].heure_debut;
                                    }
                                    return heure_debut_a - heure_debut_b;
                                }
                                self.columns[i].sort(compareFunction);  // ordonner les enregistrements de la colonne
                            }
                            if (self.view.mode_calendar) {
                                var current_max = self.view.min_time, heure_debut;
                                for (var ic=0; ic<self.columns[i].length; ic++) {
                                    event = self.columns[i][ic];

                                    if (!isNullOrUndef(event['hours_cols']) && event['hours_cols'][i]) {
                                        heure_debut = event['hours_cols'][i].heure_debut
                                    }else{
                                        heure_debut = event.heure_debut;
                                    }
                                    if (heure_debut > current_max) {
                                        record = {heure_debut: current_max, heure_fin: heure_debut}
                                        le_creneau = new PlanningCreneauIndispo(self, self.view, record, options);
                                        self.columns[i].splice(ic, 0, le_creneau);
                                        ic++;
                                    }
                                    if (!isNullOrUndef(event['hours_cols']) && event['hours_cols'][i]) {
                                        current_max = event['hours_cols'][i].heure_fin;
                                    }else{
                                        current_max = event.heure_fin;
                                    }
                                }
                                if (current_max < max_time) {
                                    record = {heure_debut: current_max, heure_fin: max_time}
                                    le_creneau = new PlanningCreneauIndispo(self, self.view, record, options);
                                    self.columns[i].push(le_creneau);
                                }
                            }
                        }
                    }
                }
            }
            return $.when()
        })
        .then(function () {  // rendu de la ligne: colonne d'entête, fillerbars, couleurs
            if (isNullOrUndef(col_index)) {
                return self.$el.html(qweb.render(self.template, {"row": self})).promise()
            }else{
                var $column = $(".of_planning_td_" + self.res_id + "_" + col_index);
                return $column.html(qweb.render('PlanningView.row.column',
                                                { "col_index": col_index , "row": self,})).promise();
            }
        })
        .then(function () {  // post-rendu de la ligne: cacher la ligne si besoin et info-bulles des fillerbars
            self.$el.attr("id", self.id);
            self.rendered = true;
            if (self.hidden) {
                self.do_hide();
            }
            if (!self.zero_horaire) {  // pas de fillerbar si pas d'horaires
                var $fillerbar, fillerbar, tooltip_options, fil_title;
                tooltip_options = {
                    delay: { show: 501, hide: 0 },
                    title: "Cet intervenant travaille plus d'heures que son maximum pour cette journée",
                }
                // ajouter les info-bulles sur les icones de warning des fillerbars
                self.$(".of_planning_fillerbar_warning").tooltip(tooltip_options);
                for (var i=0; i<self.column_nb; i++) {
                    if (isNullOrUndef(col_index) || col_index==i) {
                        $fillerbar = self.$("#of_planning_fillerbar_" + self.res_id + "_" + i);
                        fillerbar = self.fillerbars[i];

                        if (!fillerbar.nb_heures_travaillees) {
                            fil_title = "Journée non travaillée"
                        }else{
                            fil_title = "Horaires du jour: " + fillerbar["creneaux_du_jour"] + "<br/>"
                            + fillerbar["heures_occupees_str"] + " occupées sur "
                            + fillerbar["heures_travaillees_str"] + " travaillées ("
                            + fillerbar["pct_occupe"].toFixed(2) + "%)"
                        }
                        tooltip_options = {
                            delay: { show: 501, hide: 0 },
                            title: fil_title,
                        }
                        $fillerbar.tooltip(tooltip_options);
                    }
                }
            }
            if (isNullOrUndef(col_index)) return self.$el.appendTo("tbody.of_planning_table_tbody");
            return $.when();
        })
        .then(function () {  // rendu des enregistrements et créneaux dispos
            for (var i=0; i<self.column_nb; i++) {
                if (isNullOrUndef(col_index) || col_index==i) {
                    for (var j=0; j<self.columns[i].length; j++) {
                        self.columns[i][j].render(i);
                    }
                }
            }
            if (self.view.mode_calendar) {
                // ajout des lignes d'heure
                var fillerbar_height = $("#of_planning_fillerbar_"+self.res_id+"_"+0).outerHeight(true);
                var elem, hauteur;
                var duree_min_midi = 12.0 - self.view.min_time;

                var duree_debut_line, line_hour;

                for (var il=0; il<self.view.time_line.length; il++) {
                    line_hour = Math.round(self.view.time_line[il]);
                    if (self.view.min_time <= line_hour && line_hour <= self.view.max_time) {
                        for (var ic=0; ic<self.column_nb; ic++) {
                            duree_debut_line = line_hour - self.view.min_time;
                            hauteur = duree_debut_line * self.view.duree_to_px + 2;  // + 2 pour le margin
                            elem = "<span style='position: absolute; left: 0; z-index: 500; bottom: -" + hauteur +
                                "px; height: 1px; border-bottom: 1px dotted " + self.color_ft_rgba +
                                "; width: 100%; display: block;'/>"
                            $("#of_planning_fillerbar_"+self.res_id+"_"+ic).append(elem);
                        }
                        // nombres sur le coté droit
                        hauteur = duree_debut_line * self.view.duree_to_px + fillerbar_height - 8;
                        elem = "<span style='position: absolute; left: -8px; z-index: 500; top: " + hauteur +
                            "px; width: 100%; display: block;'>" +
                            line_hour + "</span>";
                        $("#of_planning_end_col_" + self.res_id).append(elem);
                    }
                }
            }
            // La ligne a été entièrement rendue
            self.trigger_up("row_rendered")
        });
    },
    /**
     *  Surcharge de la méthode parente pour ajouter la variable "row" au template XML
     */
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(qweb.render(this.template, {row: this}).trim());
        } else {
            $el = this._make_descriptive();
        }
        this.replaceElement($el);
    },
    /**
     *  Vide une colonne. n'est pas utilisée actuellement. Serait utilisé si on réparait la méthode on_reload_column
     */
    clear_column: function (col_index) {
        var record;
        while (this.columns[col_index].length) {
            record = this.columns[col_index].pop();
            record.destroy();
        }
    },
    /**
     *  Ajoute un enregistrement à la ou les colonnes concernées
     */
    add_record: function (planning_record) {
        var self = this;
        if (isNullOrUndef(planning_record.col_offset_start)) {  // foolproofing
            console.log("ERREUR: col_offset_start manquant",planning_record);
        }else if(isNullOrUndef(planning_record.col_offset_stop)) {  // évènement sur une journée
            if (isNullOrUndef(self.columns[planning_record.col_offset_start])) {
                console.log("ERREUR: col_offset_start en dehors des bornes", planning_record);
            }else{
                self.columns[planning_record.col_offset_start].push(planning_record);
                self.records_added.push(planning_record)
                self.trigger_up("record_added");
            }
        }else{
            // évènement sur plusieurs jours: calculer les heures à afficher (pour trier aussi)
            // exple: 17:00 -> 18:00 et 9:00 -> 11:30 au lieu de 2 fois 17:00 -> 11:30
            self.records_multiples[planning_record.id] = [];
            planning_record["hours_cols"] = {};
            planning_record.$of_el = {};
            var a_push, horaires_dict, first_hour;
            var descript_ft = {type: "float_time"};
            // assigner des heures de début et de fin pour les évènements sur plusieurs jours
            // pas encore complètement au point
            for (var i=planning_record.col_offset_start; i<=planning_record.col_offset_stop; i++) {
                a_push = true;

                if (i>=0 && i<self.column_nb) {
                    planning_record.$of_el[i] = planning_record.$el.clone(true);
                    planning_record["hours_cols"][i] = {};
                    if (isNullOrUndef(self.segments_horaires[self.col_offset_to_segment[i]])) {
                        planning_record["hours_cols"][i].heure_debut = false;
                        planning_record["hours_cols"][i].heure_fin = false;
                        a_push = false;
                    }else{
                        horaires_dict = self.segments_horaires[self.col_offset_to_segment[i]][2];  // récupérer le bon horaires_dict

                        if (i == planning_record.col_offset_start) {  // first day
                            // jour non travaillé. peut arriver pour une intervention de plusieurs jours qui commence le dimanche
                            if ( isNullOrUndef(horaires_dict[i + 1]) || horaires_dict[i + 1].length == 0 ) {
                                planning_record["hours_cols"][i].heure_debut = false;
                                planning_record["hours_cols"][i].heure_fin = false;
                                a_push = false;
                            }else{
                                planning_record["hours_cols"][i].heure_debut = planning_record.heure_debut;
                                // heure de fin du dernier créneau du jour
                                planning_record["hours_cols"][i].heure_fin = horaires_dict[i+1][horaires_dict[i+1].length-1][1]

                            }
                        }else if (i >= planning_record.col_offset_start && i < planning_record.col_offset_stop) {
                            // jour non travaillé
                            if ( isNullOrUndef(horaires_dict[i + 1]) || horaires_dict[i + 1].length == 0 ) {
                                planning_record["hours_cols"][i].heure_debut = false;
                                planning_record["hours_cols"][i].heure_fin = false;
                                a_push = false;
                            }else{
                                // heure de début du premier créneau du jour
                                planning_record["hours_cols"][i].heure_debut = horaires_dict[i+1][0][0]
                                // heure de fin du dernier créneau du jour
                                planning_record["hours_cols"][i].heure_fin = horaires_dict[i+1][horaires_dict[i+1].length-1][1]
                            }
                        }else if (i == planning_record.col_offset_stop) {  // last day
                            // jour non travaillé. peut arriver pour une intervention de plusieurs jours qui termine la semaine suivante
                            if ( isNullOrUndef(horaires_dict[i + 1]) || horaires_dict[i + 1].length == 0 ) {
                                planning_record["hours_cols"][i].heure_debut = false;
                                planning_record["hours_cols"][i].heure_fin = false;
                                a_push = false;
                            }else{
                                // heure de début du premier créneau du jour
                                first_hour = horaires_dict[i+1][0][0]
                                // si l'heure de début est après l'heure de fin, ramener l'heure de début à minuit
                                // peut arriver si les dates sont forcées et en dehors des horaires
                                if (first_hour > planning_record.heure_fin) {
                                    first_hour = 0.0
                                }
                                planning_record["hours_cols"][i].heure_debut = first_hour
                                planning_record["hours_cols"][i].heure_fin = planning_record.heure_fin;
                            }
                        }
                    }
                    planning_record["hours_cols"][i].heure_debut_str = formats.format_value(planning_record["hours_cols"][i].heure_debut,descript_ft);
                    planning_record["hours_cols"][i].heure_fin_str = formats.format_value(planning_record["hours_cols"][i].heure_fin,descript_ft);
                    var duree_col = planning_record["hours_cols"][i].heure_fin - planning_record["hours_cols"][i].heure_debut
                    planning_record["hours_cols"][i].duree = duree_col
                    if (self.view.mode_calendar) {
                        planning_record["hours_cols"][i].hauteur = (duree_col * self.view.duree_to_px).toString() + "px";
                    }else{
                        planning_record["hours_cols"][i].hauteur = 'auto';
                    }
                    var heures = Math.trunc(duree_col);
                    var minutes = (duree_col - heures) * 60;
                    var duree_col_str;
                    if (!heures) {
                        duree_col_str = minutes + "min";  // exple: 45min
                    }else if (!minutes) {
                        duree_col_str = heures + "h"  // exple: 2h
                    }else{
                        duree_col_str = formats.format_value(planning_record.duree,descript_ft).replace(":", "h");
                        if (duree_col_str[0] == "0") {
                            duree_col_str = duree_col_str.substring(1);  // exple: 2h45
                        }
                    }
                    // /!\ affichage de la durée erronné si l'intervention chevauche une pause. a debugguer en version 2
                    planning_record["hours_cols"][i].duree_str = duree_col_str;

                    if (a_push) {
                        self.columns[i].push(planning_record);
                    }

                    self.records_multiples[planning_record.id].push(i);
                }
                if (i == planning_record.col_offset_stop) {
                    self.records_added.push(planning_record)
                    self.trigger_up("record_added");
                }
            }
        }
    },
    /**
     *  appelée dans render(): Lance l'affectation des enregistrements aux colonnes
     *  puis envoie un signal quand ils ont tous été affectés
     */
    assing_records_to_columns: function () {
        var record_to_add;
        // Si la ligne n'a aucun enregistrement
        if (this.records_to_add.length == 0) {
            this.ready_to_render.resolve();
        }
        for (var i in this.records_to_add) {
            record_to_add = this.records_to_add[i];
            this.add_record(record_to_add);
        }
    },
    /**
     *  Vérifie que tous les enregistrements ont été assignés et le signale le cas échéant
     */
    on_record_added: function (ev) {
        if (this.records_to_add.length == this.records_added.length) {
            this.on_all_records_added()
        };
    },
    /**
     *  Signale que la ligne est prête à être rendue
     */
    on_all_records_added: function () {
        this.ready_to_render.resolve();
    },
});


var PlanningCreneauDispo = Widget.extend({
    /**
     *  Widget de créneau disponible
     */
    events: {
        'click .of_planning_creneau_action': 'on_planning_creneau_action_clicked',
        'click .of_planning_creneau_secteur_action': 'on_planning_creneau_secteur_action_clicked',
        'mouseover': 'on_mouseover',
        'mouseout': 'on_mouseout',
    },
    init: function(row, view, record, options) {
        this._super(row);
        this.row = row;
        this.creneau_type = "dispo";
        this.view = view;
        this.options = options;
        this.col_offset = options.col_offset;

        var self= this;
        this.record = record;
        this.heure_debut = record.heure_debut;
        this.heure_fin = record.heure_fin;
        var descript_ft = {type: "float_time"};
        this.heure_debut_str = formats.format_value(record.heure_debut,descript_ft);
        this.heure_fin_str = formats.format_value(record.heure_fin,descript_ft);
        this.duree = record.duree;
        this.creneaux_reels = record.creneaux_reels;
        this.warning_horaires = record.warning_horaires;
        this.secteur_id = record.secteur_id;
        this.secteur_str = record.secteur_str;
        this.display_secteur = record.display_secteur;
        var heures = Math.trunc(this.duree);
        var minutes = Math.round((this.duree - heures) * 60);
        if (!heures) {
            this.duree_str = minutes + "min";  // exple: 45min
        }else if (!minutes) {
            this.duree_str = heures + "h"  // exple: 2h
        }else{
            this.duree_str = formats.format_value(record.duree,descript_ft).replace(":", "h");
            if (this.duree_str[0] == "0") {
                this.duree_str = this.duree_str.substring(1);  // exple: 2h45
            }
        }

        this.date = moment(this.view.range_start).add(self.col_offset, 'days').format('YYYY-MM-DD');
        //utiliser la couleur des jours fériés si besoin
        if (this.view.jours_feries[this.date]) {
            this.color_bg = this.view.jours_feries_opt.color_jours_feries;
            this.ferie = true;
        }else{
            this.color_bg = this.view.creneaux_dispo.color_bg;
        }
        this.color_ft = this.view.creneaux_dispo.color_ft;
        this.lieu_debut = record.lieu_debut;
        this.lieu_fin = record.lieu_fin;

        if (this.view.mode_calendar) {
            this.hauteur = ((this.heure_fin - this.heure_debut) * this.view.duree_to_px).toString() + "px";
        }else{
            this.hauteur = "auto";
        }

        // inhiber double-clique
        this.on_planning_creneau_secteur_action_clicked = _.debounce(
            this.on_planning_creneau_secteur_action_clicked, 300, true);
        this.on_planning_creneau_action_clicked = _.debounce(this.on_planning_creneau_action_clicked, 300, true);
    },
    /**
     *  génère le rendu visuel du créneau et l'attache à la colonne correspondante
     */
    render: function(col_index=null, reload=false) {
        var self = this;
        if (isNullOrUndef(col_index)) {
            col_index = self.col_offset;
        }
        if (reload) {
            return self.row.render(col_index, true);
        }else{
            return self.$el.html(qweb.render('PlanningView.creneau_dispo', {"creneau": self, "col_index": col_index})).promise()
            .then(function (){
                var td_id = "of_planning_td_" + self.row.res_id + "_" + col_index;
                self.$el.appendTo("#" + td_id);
            })
        }

    },
    /**
     *  récupère le secteur dans la BDD puis re-génère le rendu
     */
    reload_secteur: function() {
        var self = this;
        var tournee_mod = new Model("of.planning.tournee")
        return tournee_mod.query(['id', 'employee_id', 'date', 'secteur_id']) // retrieve secteur from db
            .filter([['employee_id','=', self.row.res_id], ['date','=', self.date]])
            .limit(1)
            .all()
            .then(function (result){
                if (result.length == 1) {
                    var i = self.col_offset, creneau;
                    for (var j=0; j<self.row.columns[i].length; j++) {
                        creneau = self.row.columns[i][j];
                        if (creneau.creneau_type == "dispo") {
                            if (!result[0].secteur_id) {
                                creneau.secteur_id = false;
                                creneau.secteur_str = "";
                            }else{
                                creneau.secteur_id = result[0].secteur_id[0];
                                creneau.secteur_str = result[0].secteur_id[1];
                            }
                        }
                    }
                }
                return self.render(null,true);
            });
    },
    /**
     *  Lance le signal pour recharger tous les évènements
     */
    reload_events: function () {
        this.trigger_up('reload_events');
    },
    reload_column: function () {
        this.view.on_reload_column(this.row.res_id, this.col_offset);
    },
    /**
     *  Vérifie si la div est trop petite pour son contenu
     */
    isOverflown: function() {
        var el = this.$el.find('.of_planning_creneau_dispo')[0];
        return el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;
    },
    /**
     *  agrandi la div si besoin
     */
    on_mouseover: function (ev) {
        ev.preventDefault();
        if (this.view.mode_calendar && this.isOverflown()) {
            this.$el.find('.of_planning_creneau_dispo').height('auto');
        }
    },
    /**
     *  remet la div à sa taille originelle
     */
    on_mouseout: function (ev) {
        ev.preventDefault();
        if (this.view.mode_calendar) {
            if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                var rect1 = ev.relatedTarget.getBoundingClientRect();
                var rect2 = this.$el.find('.of_planning_creneau_dispo')[0].getBoundingClientRect();
                var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                if (overlap) {
                    return;
                }
            }
            if (!this.$el.is(":hover")) {
                this.$el.find('.of_planning_creneau_dispo').outerHeight(this.hauteur);
            }
        }
    },
    /**
     *  Ouvre le pop-up de sélection de secteur
     */
    on_planning_creneau_secteur_action_clicked: function(ev){
        ev.preventDefault();
        var self = this;
        var action_id = "of_planning_view.action_view_of_planif_creneau_secteur_wizard"
        var additional_context = {
            "default_date_creneau": self.date,
            "default_employee_id": self.row.res_id,
            "default_secteur_id": self.secteur_id,
        };

        return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
                var options = {
                    // pour une raison inconnue le additional_context n'est pas pris en compte avant
                    'additional_context': pyeval.eval('context', additional_context),
                    'on_close': function () {self.reload_secteur();},
                };
                return self.view.ViewManager.action_manager.do_action(result,options);
            })
    },
    /**
     *  handler de clique sur action
     */
    on_planning_creneau_action_clicked: function(ev){
        ev.preventDefault();
        var self = this;
        var action_id = $(ev.currentTarget).attr('action_id')
        if (action_id == "of_planning_view.action_view_of_planif_wizard") {
            return self.action_wizard_planif();
        }else if (action_id == "of_planning_view.action_view_of_planning_intervention_form_wizard") {
            return self.action_creer_rdv();
        }else{
            console.log("Action inconnue...")
        }
    },
    /**
     *  Ouvre le pop-up de planification
     */
    action_wizard_planif: function() {
        var self = this;
        var action_id = "of_planning_view.action_view_of_planif_wizard"
        var additional_context = {
            "default_heure_debut_creneau": self.heure_debut,
            "default_heure_debut_rdv": self.heure_debut,
            "default_heure_fin_creneau": self.heure_fin,
            "default_lieu_prec_id": self.lieu_debut.id || false,
            "default_lieu_suiv_id": self.lieu_fin.id || false,
            "default_date_creneau": self.date,
            "default_duree_creneau": self.duree,
            "default_employee_id": self.row.res_id,
            "default_secteur_id": self.secteur_id,
            "default_creneaux_reels": self.creneaux_reels.length > 0 ? self.creneaux_reels : false,
            "default_warning_horaires": self.warning_horaires,
        };

        return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
                var options = {
                    // pour une raison inconnue le additional_context n'est pas pris en compte avant
                    'additional_context': pyeval.eval('context', additional_context),
                    'on_close': function () {self.reload_events();},
                };
                return self.view.ViewManager.action_manager.do_action(result,options);
            }).then(function(){
                $(".o_form_buttons_edit").eq(0).hide();  // cacher les boutons "Sauvergarder" et "Annuler"
            });
    },
    /**
     *  Ouvre le pop-up de création de rdv
     */
    action_creer_rdv: function() {
        var self = this;
        var action_id = "of_planning_view.action_view_of_planning_intervention_form_wizard"
        // contournement : "new Date(xxx)" n'est pas supporté par safari et IE
        var la_date = moment(self.date + " " + self.heure_debut_str + ":00" + self.row.tz_offset);
        var la_date = la_date._d;

        var additional_context = _.extend(self.view.dataset.context, {
            "default_employee_ids": [[6, 0, [self.row.res_id]]],
            "default_date": moment.utc(la_date.toUTCString()).format('YYYY-MM-DD HH:mm:ss'),
            "default_origin_interface": "Manuelle (vue planning)",
        });
        return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
                var options = {
                    // pour une raison inconnue le additional_context n'est pas pris en compte avant
                    'additional_context': pyeval.eval('context', additional_context),
                    'on_close': function () {self.reload_events();},
                };
                return self.view.ViewManager.action_manager.do_action(result,options);
            });
    },
});


var PlanningCreneauIndispo = Widget.extend({
    /**
     *  Widget de créneau indisponible
     */
    init: function(row, view, record, options) {
        this._super(row);
        this.row = row;
        this.creneau_type = "indispo";
        this.view = view;
        this.options = options;
        this.col_offset = options.col_offset;

        var self= this;
        this.record = record;
        this.heure_debut = record.heure_debut;
        this.heure_fin = record.heure_fin;
        var descript_ft = {type: "float_time"};
        this.heure_debut_str = formats.format_value(record.heure_debut,descript_ft);
        this.heure_fin_str = formats.format_value(record.heure_fin,descript_ft);
        this.duree = this.heure_fin - this.heure_debut;
        var heures = Math.trunc(this.duree);
        var minutes = Math.round((this.duree - heures) * 60);
        if (!heures) {
            this.duree_str = minutes + "min";  // exple: 45min
        }else if (!minutes) {
            this.duree_str = heures + "h"  // exple: 2h
        }else{
            this.duree_str = formats.format_value(this.duree,descript_ft).replace(":", "h");
            if (this.duree_str[0] == "0") {
                this.duree_str = this.duree_str.substring(1);  // exple: 2h45
            }
        }

        this.date = moment(this.view.range_start).add(self.col_offset, 'days').format('YYYY-MM-DD');

        if (this.view.mode_calendar) {
            this.hauteur = ((this.heure_fin - this.heure_debut) * this.view.duree_to_px).toString() + "px";
        }else{
            this.hauteur = "auto";
        }
    },
    /**
     *  génère le rendu visuel du créneau et l'attache à la colonne correspondante
     */
    render: function(col_index) {
        var self = this;
        if (isNullOrUndef(col_index)) {
            col_index = self.col_offset;
        }
        return self.$el.html(qweb.render('PlanningView.creneau_indispo', {"creneau": self, "col_index": col_index})).promise()
            .then(function (){
                var td_id = "of_planning_td_" + self.row.res_id + "_" + col_index;
                self.$el.appendTo("#" + td_id);
            })
    },
});


var PlanningRecord = Widget.extend({
    /**
     *  Widget de RDV d'intervention
     */
    events: {
        'mouseover': 'on_mouseover',
        'mouseout': 'on_mouseout',
    },
    init: function(row, view, record, options) {
        this.id = record.id;
        this._super(row);
        this.row = row;
        this.creneau_type = "intervention";
        this.view = view;
        this.options = options;
        this.day_span = options.day_span;
        if (this.day_span > 1) this.$els = [];
        this.class ="of_planning_record of_planning_record_" + this.id;
        if (!isNullOrUndef(record.state_int)) this.class += " of_calendar_state_" + record["state_int"];
        if (this.day_span > 1) this.class += " of_planning_record_multiple";
        if (record.state_int == 3) {
            this.class += " of_planning_info_annule_reporte";
            this.annule_reporte = true;
        }else{
            this.annule_reporte = false;
        }
        this.col_offset_start = options.col_offset_start;
        this.col_offset_stop = options.col_offset_stop;
        this.read_only_mode = options.read_only_mode || true; // current implementation solo readonly

        this.date_start = record[this.view.date_start];
        this.date_stop = record[this.view.date_stop];

        var self= this;
        this.record = record;
        if (this.view.mode_calendar) {
            this.hauteur = (record.duree_debut_fin * this.view.duree_to_px).toString() + "px";
        }else{
            this.hauteur = "auto";
        }
        // formattage des heures et durées
        var descript_dt = {type: "datetime"};
        var descript_ft = {type: "float_time"};
        this.heure_debut_str = formats.format_value(this.date_start, descript_dt).substring(11, 16);
        this.heure_fin_str = formats.format_value(this.date_stop, descript_dt).substring(11, 16);
        this.heure_debut = hh_mm_to_float(this.heure_debut_str)
        this.heure_fin = hh_mm_to_float(this.heure_fin_str)
        this.duree = record.duree_prompt
        var heures = Math.trunc(this.duree);
        var minutes = Math.round((this.duree - heures) * 60);
        if (!heures) {
            this.duree_str = minutes + "min";  // exple: 45min
        }else if (!minutes) {
            this.duree_str = heures + "h"  // exple: 2h
        }else{
            this.duree_str = formats.format_value(this.duree,descript_ft).replace(":", "h");
            if (this.duree_str[0] == "0") {
                this.duree_str = this.duree_str.substring(1);  // exple: 2h45
            }
        }
        this.address_city = record.address_city;
        this.address_zip = record.address_zip;
        this.secteur_name = record.secteur_id && record.secteur_id[1] || false;
        this.name = record.name;
        this.partner_name = record.partner_name;
        this.mobile = record.mobile;
        this.phone = record.phone;
        this.tache_name = record.tache_name;
        this.name = record.name;
        this.state_int = record.state_int;
        this.employee_names = record.employee_names;
        this.tag_names = record.tag_names;
        this.tooltip_description = record.tooltip_description;
        this.session.user_has_group('of_planning.of_group_planning_intervention_flexibility').then(function(has_group) {
            if(has_group) {
                self.flexible = record.flexible;
            } else {
                self.flexible = false;
            }
        });

        if (record[this.view.resource].length > 1) {  // several attendees
            this.attendee_other_ids = _.reject(record[this.view.resource], function (attendee_id) { return attendee_id == self.row.res_id})
        }else{
            this.attendee_other_ids = []
        }
        this.on_global_click = _.debounce(this.on_global_click, 300, true);
    },
    /**
     *  Génère le rendu de l'enregistrement. associe les events js.
     */
    render: function(col_index) {
        var self = this;

        if (isNullOrUndef(col_index)) {  // foolproofing
            col_index = Math.max(self.col_offset_start, 0);
        }
        var color_captions = false;
        if (self.view.color_multiple) {
            var color_filter = self.view.sidebar.color_filter
            var current_filter = color_filter.color_filter_data[color_filter.current_radio_key]
            color_captions = current_filter.captions
        }
        if (color_captions) {
            var caption_key = self.record[current_filter.field]
            if (typeof caption_key === "object") { // make sure caption_key is an integer before testing captions[caption_key]
                caption_key = caption_key[0];
            }
            if (isNullOrUndef(color_captions[caption_key])) {
                if (!isNullOrUndef(color_captions[-1])) {
                    self.color_ft = color_captions[-1]["color_ft"];
                    self.color_bg = color_captions[-1]["color_bg"];
                }else{
                    self.color_ft = "#0D0D0D";
                    self.color_bg = "#F0F0F0";
                }
            }else{
                self.color_ft = color_captions[caption_key]["color_ft"];
                self.color_bg = color_captions[caption_key]["color_bg"];
            }
        }else{
            self.color_bg = self.row.color_bg;
            self.color_ft = self.row.color_ft;
        }

        if (isNullOrUndef(self.col_offset_stop)) {  // 1 day event
            return self.$el.html(qweb.render('PlanningView.record', {"record": self, "col_index": col_index})).promise()
                .then(function (){
                    var td_id = "of_planning_td_" + self.row.res_id + "_" + col_index;
                    self.$el.appendTo("#" + td_id);
                    self.$el.on('click', self.proxy('on_global_click'));
                    self.$el.mouseover(self.on_planning_record_mouseover);
                    self.$el.mouseout(self.on_planning_record_mouseout);
                    var tooltip_opts = {
                        delay: { show: 501, hide: 0 },
                    }
                    return qweb.render('PlanningView.record.tooltip', {"record": self, "col_index": self.col_offset_start})
                }).then(function (html) {  // info-bulle
                    self.tooltip_opts = {
                        delay: { show: 501, hide: 0 },
                        title: html,
                    }
                    return self.$el.tooltip(self.tooltip_opts);
                });
        }
        return self.$of_el[col_index].html(qweb.render('PlanningView.record', {"record": self, "col_index": col_index})).promise()
            .then(function (){
                var td_id = "of_planning_td_" + self.row.res_id + "_" + col_index;
                self.$of_el[col_index].appendTo("#" + td_id);
                self.$of_el[col_index].on('click', self.proxy('on_global_click'));
                self.$of_el[col_index].mouseover(self.on_planning_record_mouseover);
                self.$of_el[col_index].mouseout(self.on_planning_record_mouseout);
                if (isNullOrUndef(self.tooltip_opts)) {
                    return qweb.render('PlanningView.record.tooltip', {"record": self, "col_index": self.col_offset_start});
                }
                return $.when();
            }).then(function (html) {  // info-bulle
                if (isNullOrUndef(self.tooltip_opts)) {
                    self.tooltip_opts = {
                        delay: { show: 501, hide: 0 },
                        title: html,
                    }
                    for (var k in self.$of_el){
                        self.$of_el[k].tooltip(self.tooltip_opts)
                    }
                }

            });
    },
    /**
     *  Vérifie si la div est trop petite pour son contenu
     */
    isOverflown: function() {
        var el = this.$el.find('.of_planning_record_global_click')[0];
        if (isNullOrUndef(el)) {
            return false;
        }
        return el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;
    },
    /**
     *  agrandi la div si besoin
     */
    on_mouseover: function (ev) {
        ev.preventDefault();
        if (this.view.mode_calendar && this.day_span > 1) {
            // à cause de l'asynchronicité de find() on ne peut pas utiliser de boucle for
            var a = new Array(7);
            a[0] = this.$of_el[0] && this.$of_el[0].find('.of_planning_record_global_click')[0] || false;
            a[1] = this.$of_el[1] && this.$of_el[1].find('.of_planning_record_global_click')[0] || false;
            a[2] = this.$of_el[2] && this.$of_el[2].find('.of_planning_record_global_click')[0] || false;
            a[3] = this.$of_el[3] && this.$of_el[3].find('.of_planning_record_global_click')[0] || false;
            a[4] = this.$of_el[4] && this.$of_el[4].find('.of_planning_record_global_click')[0] || false;
            a[5] = this.$of_el[5] && this.$of_el[5].find('.of_planning_record_global_click')[0] || false;
            a[6] = this.$of_el[6] && this.$of_el[6].find('.of_planning_record_global_click')[0] || false;
            if (!!a[0] && (a[0].scrollHeight > a[0].clientHeight || a[0].scrollWidth > a[0].clientWidth)) {
                this.$of_el[0].find('.of_planning_record_global_click').height('auto');
            }
            if (!!a[1] && (a[1].scrollHeight > a[1].clientHeight || a[1].scrollWidth > a[1].clientWidth)) {
                this.$of_el[1].find('.of_planning_record_global_click').height('auto');
            }
            if (!!a[2] && (a[2].scrollHeight > a[2].clientHeight || a[2].scrollWidth > a[2].clientWidth)) {
                this.$of_el[2].find('.of_planning_record_global_click').height('auto');
            }
            if (!!a[3] && (a[3].scrollHeight > a[3].clientHeight || a[3].scrollWidth > a[3].clientWidth)) {
                this.$of_el[3].find('.of_planning_record_global_click').height('auto');
            }
            if (!!a[4] && (a[4].scrollHeight > a[4].clientHeight || a[4].scrollWidth > a[4].clientWidth)) {
                this.$of_el[4].find('.of_planning_record_global_click').height('auto');
            }
            if (!!a[5] && (a[5].scrollHeight > a[5].clientHeight || a[5].scrollWidth > a[5].clientWidth)) {
                this.$of_el[5].find('.of_planning_record_global_click').height('auto');
            }
            if (!!a[6] && (a[6].scrollHeight > a[6].clientHeight || a[6].scrollWidth > a[6].clientWidth)) {
                this.$of_el[6].find('.of_planning_record_global_click').height('auto');
            }
        }else if (this.view.mode_calendar && this.isOverflown()) {
            this.$el.find('.of_planning_record_global_click').height('auto');
        }
    },
    /**
     *  remet la div à sa taille originelle
     */
    on_mouseout: function (ev) {
        ev.preventDefault();
        if (this.view.mode_calendar && this.day_span > 1) {
            // à cause de l'asynchronicité de find() on ne peut pas utiliser de boucle for
            var a = new Array(7);
            a[0] = this.$of_el[0] && this.$of_el[0].find('.of_planning_record_global_click')[0] || false;
            a[1] = this.$of_el[1] && this.$of_el[1].find('.of_planning_record_global_click')[0] || false;
            a[2] = this.$of_el[2] && this.$of_el[2].find('.of_planning_record_global_click')[0] || false;
            a[3] = this.$of_el[3] && this.$of_el[3].find('.of_planning_record_global_click')[0] || false;
            a[4] = this.$of_el[4] && this.$of_el[4].find('.of_planning_record_global_click')[0] || false;
            a[5] = this.$of_el[5] && this.$of_el[5].find('.of_planning_record_global_click')[0] || false;
            a[6] = this.$of_el[6] && this.$of_el[6].find('.of_planning_record_global_click')[0] || false;
            if (!!a[0]) {
                if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                    var rect1 = ev.relatedTarget.getBoundingClientRect();
                    var rect2 = this.$of_el[0].find('.of_planning_record_global_click')[0].getBoundingClientRect();
                    var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                    if (overlap) {
                        return;
                    }
                }
                this.$of_el[0].find('.of_planning_record_global_click').outerHeight(this.hours_cols[0].hauteur);
            }
            if (!!a[1]) {
                if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                    var rect1 = ev.relatedTarget.getBoundingClientRect();
                    var rect2 = this.$of_el[1].find('.of_planning_record_global_click')[0].getBoundingClientRect();
                    var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                    if (overlap) {
                        return;
                    }
                }
                this.$of_el[1].find('.of_planning_record_global_click').outerHeight(this.hours_cols[1].hauteur);
            }
            if (!!a[2]) {
                if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                    var rect1 = ev.relatedTarget.getBoundingClientRect();
                    var rect2 = this.$of_el[2].find('.of_planning_record_global_click')[0].getBoundingClientRect();
                    var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                    if (overlap) {
                        return;
                    }
                }
                this.$of_el[2].find('.of_planning_record_global_click').outerHeight(this.hours_cols[2].hauteur);
            }
            if (!!a[3]) {
                if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                    var rect1 = ev.relatedTarget.getBoundingClientRect();
                    var rect2 = this.$of_el[3].find('.of_planning_record_global_click')[0].getBoundingClientRect();
                    var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                    if (overlap) {
                        return;
                    }
                }
                this.$of_el[3].find('.of_planning_record_global_click').outerHeight(this.hours_cols[3].hauteur);
            }
            if (!!a[4]) {
                if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                    var rect1 = ev.relatedTarget.getBoundingClientRect();
                    var rect2 = this.$of_el[4].find('.of_planning_record_global_click')[0].getBoundingClientRect();
                    var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                    if (overlap) {
                        return;
                    }
                }
                this.$of_el[4].find('.of_planning_record_global_click').outerHeight(this.hours_cols[4].hauteur);
            }
            if (!!a[5]) {
                if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                    var rect1 = ev.relatedTarget.getBoundingClientRect();
                    var rect2 = this.$of_el[5].find('.of_planning_record_global_click')[0].getBoundingClientRect();
                    var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                    if (overlap) {
                        return;
                    }
                }
                this.$of_el[5].find('.of_planning_record_global_click').outerHeight(this.hours_cols[5].hauteur);
            }
            if (!!a[6]) {
                if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                    var rect1 = ev.relatedTarget.getBoundingClientRect();
                    var rect2 = this.$of_el[6].find('.of_planning_record_global_click')[0].getBoundingClientRect();
                    var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                    if (overlap) {
                        return;
                    }
                }
                this.$of_el[6].find('.of_planning_record_global_click').outerHeight(this.hours_cols[6].hauteur);
            }
        }else if (this.view.mode_calendar) {
            if (ev.relatedTarget && ev.relatedTarget.parentNode.classList.contains('of_planning_fillerbar')) {
                var rect1 = ev.relatedTarget.getBoundingClientRect();
                var rect2 = this.$el.find('.of_planning_record_global_click')[0].getBoundingClientRect();
                var overlap = !(rect1.right < rect2.left || rect1.left > rect2.right || rect1.bottom - 1 < rect2.top || rect1.top > rect2.bottom - 1)
                if (overlap) {
                    return;
                }
            }
            this.$el.find('.of_planning_record_global_click').outerHeight(this.hauteur);
        }
    },
    /**
     *  méthode reprise de KanbanView
     */
    on_global_click: function (ev) {
        if ($(ev.target).parents('.o_dropdown_kanban').length) {
            return;
        }
        if (!ev.isTrigger) {
            var trigger = true;
            var elem = ev.target;
            var ischild = true;
            var children = [];
            while (elem) {
                var events = $._data(elem, 'events');
                if (elem == ev.currentTarget) {
                    ischild = false;
                }
                var test_event = events && events.click && (events.click.length > 1 || events.click[0].namespace !== "tooltip");
                if (ischild) {
                    children.push(elem);
                    if (test_event) {
                        // do not trigger global click if one child has a click event registered
                        trigger = false;
                    }
                }
                if (trigger && test_event) {
                    _.each(events.click, function(click_event) {
                        if (click_event.selector) {
                            // For each parent of original target, check if a
                            // delegated click is bound to any previously found children
                            _.each(children, function(child) {
                                if ($(child).is(click_event.selector)) {
                                    trigger = false;
                                }
                            });
                        }
                    });
                }
                elem = elem.parentElement;
            }
            if (trigger) {
                this.on_card_clicked(ev);
            }
        }
    },
    /**
     *  Donner un effet de pulsation à tous les planning_record du même évènement
     */
    on_planning_record_mouseover: function(ev) {
        var record_class = "of_planning_record_" + this.id;
        var records = $("." + record_class)
        if (records.length > 1) {
            records.addClass("of_pulse");
        }
        var self = this;
    },
    /**
     *  Retire l'effet de pulsation
     */
    on_planning_record_mouseout: function(ev) {
        var record_class = "of_planning_record_" + this.id;
        var records = $("." + record_class)
        if (records.length > 1) {
            records.removeClass("of_pulse");
        }
    },
    /*
     *  ouvre le form de l'évènement
     */
    on_card_clicked: function() {
        this.trigger_up('planning_record_open', {id: this.id});
    },
});


PlanningView.Sidebar = Widget.extend({
    template: 'PlanningView.sidebar',
    // Widget du panneau latéral droit
    /**
     *  Créé la légende états, les filtres de ressource et les filtres d'informations affichées
     */
    start: function() {
        var self = this;
        this.view = this.getParent()
        this.caption = new SidebarCaption(this, this.view);
        this.reso_filter = new PlanningView.SidebarResoFilter(this, this.view);
        this.info_filter = new PlanningView.SidebarInfoFilter(this, this.view);
        var dfd_color_filter = $.Deferred();
        if (this.view.color_multiple) {
            this.color_filter = new SidebarColorFilter(this, this.view);
            dfd_color_filter = this.color_filter.appendTo(this.$el).promise()
        }else{
            dfd_color_filter.resolve()
        }
        return $.when(this._super(),
                      this.reso_filter.appendTo(this.$el),
                      this.info_filter.appendTo(this.$el),
                      this.caption.appendTo(this.$el),
                      dfd_color_filter)
        .then(function() {
            self.caption.render();
            if (!isNullOrUndef(self.color_filter)) {
                self.color_filter.render();
            }
        });
    }
});


PlanningView.SidebarResoFilter = Widget.extend({
    // widget des filtres de ressource, ou attendees
    events: {
        'click .of_planning_contacts': 'on_click',
    },
    template: 'PlanningView.sidebar.reso_filters',

    init: function(parent, view) {
        this._super(parent);
        this.view = view;
    },
    /**
     *  Appelé dans le _do_search de la vue
     */
    render: function() {
        var self = this;
        return self.$('.of_planning_contacts')
            .html(qweb.render('PlanningView.sidebar.contacts', { filters: self.view.all_filters }))
    },
    on_click: function(e) {
        var ir_values_model = new Model('ir.values');
        if (e.target.tagName == 'SPAN') {  // click sur span -> la checkboxe est a coté
            var la_input = e.target.previousElementSibling.firstElementChild;
            $("#"+la_input.id).click();
            return;
        }
        if (e.target.tagName == 'DIV') {
            $(e.target).find('input').click();
            return;
        }

        this.view.all_filters[this.view.res_ids_indexes[e.target.value]].is_checked = e.target.checked;
        if (e.target.checked) {
            // Ajoute l'id aux filtres sélectionné et sauvegarde la sélection
            this.view.filter_attendee_ids.push(parseInt(e.target.value));
            ir_values_model.call("set_default",
                ["of.intervention.settings",
                "of_filter_attendee_ids",
                this.view.filter_attendee_ids, false]);
        }else{
            // Retire l'id des filtres sélectionnés et sauvegarde la sélection
            for (var i=0; i<this.view.filter_attendee_ids.length; i++) {
                if (this.view.filter_attendee_ids[i] == e.target.value) {
                    this.view.filter_attendee_ids.splice(i, 1);
                }
            }
            ir_values_model.call("set_default",
                ["of.intervention.settings",
                "of_filter_attendee_ids",
                this.view.filter_attendee_ids, false]);
        }
        // Affiche / Cache la ligne
        var row_id = "of_planning_row_"+e.target.value;
        var la_row = this.view.rows[this.view.rows_ids_indexes[e.target.value]];
        la_row.hidden = !e.target.checked;
        la_row.do_toggle(e.target.checked);
    },
});


PlanningView.SidebarInfoFilter = Widget.extend({
    events: {
        'click .of_planning_ev_infos': 'on_click',
        'click .of_planning_info_filter_show': 'on_click_show_filters',
        'click .of_planning_info_filter_hide': 'on_click_hide_filters',
    },
    template: 'PlanningView.sidebar.info_filters',

    init: function(parent, view) {
        var self = this;
        this._super(parent);
        this.view = view;
        this.info_filters_visible = (local_storage.getItem('planningview_info_filters_visible') == 'true');
        local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        $.when(this.init_filters()).then(function(){self.render()});
    },
    init_filters: function() {
        var self = this;

        var check_tab_names = [
            "name", "partner_name", "mobile", "phone", "tache", "zip", "city", "secteur", "heure_debut", "heure_fin",
            "duree", "annule_reporte"];
        var check_tab_vals = new Array(12);
        var check_tab_defs = new Array(12);
        var dfd = $.Deferred();
        var p = dfd.promise(self.info_filters);
        var defs = [], proms = [], les_args, le_def;
        var ir_values_model = new Model("ir.values");
        // @todo: trouver une meilleure façon de faire ça
        // Je n'ai pas réussi à faire fonctionner une boucle for pour ça
        // du fait de l'asynchronisme. la variable i arrive à son max avant de recevoir les réponses asynchrones
        // et du coup seul check_tab_vals[i_max] est affecté
        // Il existe une solution mais elle prendrait du temps à comprendre et appliquer à notre cas
        // Du coup on verra plus tard
        // Récupère la dernière sélection des filtres d'info
        check_tab_defs[0] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[0], false]);
        $.when(check_tab_defs[0]).then(function(res){check_tab_vals[0] = isNullOrUndef(res) || res});
        check_tab_defs[1] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[1], false]);
        $.when(check_tab_defs[1]).then(function(res){check_tab_vals[1] = isNullOrUndef(res) || res});
        check_tab_defs[2] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[2], false]);
        $.when(check_tab_defs[2]).then(function(res){check_tab_vals[2] = isNullOrUndef(res) || res});
        check_tab_defs[3] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[3], false]);
        $.when(check_tab_defs[3]).then(function(res){check_tab_vals[3] = isNullOrUndef(res) || res});
        check_tab_defs[4] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[4], false]);
        $.when(check_tab_defs[4]).then(function(res){check_tab_vals[4] = isNullOrUndef(res) || res});
        check_tab_defs[5] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[5], false]);
        $.when(check_tab_defs[5]).then(function(res){check_tab_vals[5] = isNullOrUndef(res) || res});
        check_tab_defs[6] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[6], false]);
        $.when(check_tab_defs[6]).then(function(res){check_tab_vals[6] = isNullOrUndef(res) || res});
        check_tab_defs[7] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[7], false]);
        $.when(check_tab_defs[7]).then(function(res){check_tab_vals[7] = isNullOrUndef(res) || res});
        check_tab_defs[8] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[8], false]);
        $.when(check_tab_defs[8]).then(function(res){check_tab_vals[8] = isNullOrUndef(res) || res});
        check_tab_defs[9] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[9], false]);
        $.when(check_tab_defs[9]).then(function(res){check_tab_vals[9] = isNullOrUndef(res) || res});
        check_tab_defs[10] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[10], false]);
        $.when(check_tab_defs[10]).then(function(res){check_tab_vals[10] = isNullOrUndef(res) || res});
        check_tab_defs[11] = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_" + check_tab_names[11], false]);
        $.when(check_tab_defs[11]).then(function(res){check_tab_vals[11] = isNullOrUndef(res) || res});

        $.when.apply($, check_tab_defs)
        .then(function () {
            // créer le dictionnaire utilisé pour le rendu et les events de click
            self.info_filters = {
                "name": {
                    "value": "name",
                    "input_id": "name_input",
                    "class": "of_planning_info_name",
                    "label": "Libellé",
                    "is_checked": check_tab_vals[0],
                    "field_name_ir": "planningview_filter_name",
                },
                "partner": {
                    "value": "partner",
                    "input_id": "partner_input",
                    "class": "of_planning_info_partner",
                    "label": "Client",
                    "is_checked": check_tab_vals[1] || check_tab_vals[2] || check_tab_vals[3],
                    "child_filters_visible": (local_storage.getItem('planningview_info_filters_visible_partner') == 'true'),
                    "child_filters": {
                        "partner_name": {
                            "value": "partner-partner_name",
                            "input_id": "partner-partner_name_input",
                            "class": "of_planning_subinfo_partner_name",
                            "label": "Nom",
                            "is_checked": check_tab_vals[1],
                            "field_name_ir": "planningview_filter_partner_name",
                        },
                        "mobile": {
                            "value": "partner-mobile",
                            "input_id": "partner-mobile_input",
                            "class": "of_planning_subinfo_mobile",
                            "label": "Mobile",
                            "is_checked": check_tab_vals[2],
                            "field_name_ir": "planningview_filter_mobile",
                        },
                        "phone": {
                            "value": "partner-phone",
                            "input_id": "partner-phone_input",
                            "class": "of_planning_subinfo_phone",
                            "label": "Fixe",
                            "is_checked": check_tab_vals[3],
                            "field_name_ir": "planningview_filter_phone",
                        },
                    },
                },
                "tache": {
                    "value": "tache",
                    "input_id": "tache_input",
                    "class": "of_planning_info_tache_name",
                    "label": "Tache",
                    "is_checked": check_tab_vals[4],
                    "field_name_ir": "planningview_filter_tache",
                },
                "lieu": {
                    "value": "lieu",
                    "input_id": "lieu_input",
                    "class": "of_planning_info_lieu",
                    "label": "Lieu",
                    "is_checked": check_tab_vals[5] || check_tab_vals[6] || check_tab_vals[7],
                    "child_filters_visible": (local_storage.getItem('planningview_info_filters_visible_lieu') == 'true'),
                    "child_filters": {
                        "zip": {
                            "value": "lieu-zip",
                            "input_id": "lieu-zip_input",
                            "class": "of_planning_subinfo_zip",
                            "label": "Code postal",
                            "is_checked": check_tab_vals[5],
                            "field_name_ir": "planningview_filter_zip",
                        },
                        "city": {
                            "value": "lieu-city",
                            "input_id": "lieu-city_input",
                            "class": "of_planning_subinfo_city",
                            "label": "Ville",
                            "is_checked": check_tab_vals[6],
                            "field_name_ir": "planningview_filter_city",
                        },
                        "secteur": {
                            "value": "lieu-secteur",
                            "input_id": "lieu-secteur_input",
                            "class": "of_planning_subinfo_secteur",
                            "label": "Secteur",
                            "is_checked": check_tab_vals[7],
                            "field_name_ir": "planningview_filter_secteur",
                        },
                    },
                },
                "heures": {
                    "value": "heures",
                    "input_id": "heures_input",
                    "class": "of_planning_info_heures",
                    "label": "Heures / Durées",
                    "is_checked": check_tab_vals[8] || check_tab_vals[9] || check_tab_vals[10],
                    "child_filters_visible": (local_storage.getItem('planningview_info_filters_visible_heures') == 'true'),
                    "child_filters": {
                        "heure_debut": {
                            "value": "heures-heure_debut",
                            "input_id": "heures-heure_debut_input",
                            "class": "of_planning_subinfo_heure_debut",
                            "label": "Heure de début",
                            "is_checked": check_tab_vals[8],
                            "field_name_ir": "planningview_filter_heure_debut",
                        },
                        "heure_fin": {
                            "value": "heures-heure_fin",
                            "input_id": "heures-heure_fin_input",
                            "class": "of_planning_subinfo_heure_fin",
                            "label": "Heure de fin",
                            "is_checked": check_tab_vals[9],
                            "field_name_ir": "planningview_filter_heure_fin",
                        },
                        "duree": {
                            "value": "heures-duree",
                            "input_id": "heures-duree_input",
                            "class": "of_planning_subinfo_duree",
                            "label": "Durée",
                            "is_checked": check_tab_vals[10],
                            "field_name_ir": "planningview_filter_duree",
                        },
                    },
                },
                "annule_reporte": {
                    "value": "annule_reporte",
                    "input_id": "annule_reporte_input",
                    "class": "of_planning_info_annule_reporte",
                    "label": "Annulé / Reporté",
                    "is_checked": check_tab_vals[11],
                    "field_name_ir": "planningview_filter_annule_reporte",
                    "separated": true,
                },
            }
            self.view.info_filters = self.info_filters;
            dfd.resolve();
        });

        return p;
    },
    /**
     *  Génère le rendu et cache les filtres en fonction de l'état lors du dernier affichage de la vue planning
     *  par l'utilisateur. Appelé par on_all_rows_rendered
     */
    render: function() {
        var self = this;

        $.when(self.$('.of_planning_ev_infos').html(qweb.render('PlanningView.sidebar.event_info', { filters: self.info_filters })))
        .then(function() {
            self.rendered = true;
            self.apply_filters();
            if (self.info_filters_visible == 'true' || self.info_filters_visible) {
                self.$('.of_planning_ev_infos').removeClass("o_hidden");
                self.$(".of_planning_info_filter_show").addClass("o_hidden");
                self.$(".of_planning_info_filter_hide").removeClass("o_hidden");
                for (var f in self.info_filters) {
                    if (!isNullOrUndef(self.info_filters[f].child_filters) && self.info_filters[f].child_filters_visible) {
                        $(".of_planning_ev_info_toggle_" + f).toggleClass("o_hidden");  // toggle arrow down/up
                        $(".of_planning_ev_subinfo_" + f).removeClass("o_hidden");  // toggle child_filters visible
                    }
                }
            }
        });

    },
    /**
     *  Applique les filtres aux évènements. Appelé par on_all_rows_rendered
     */
    apply_filters: function () {
        for (var f in this.info_filters) {
            var le_filter = this.info_filters[f], le_sub;
            var la_class = le_filter.class;
            if (le_filter.is_checked) {  // update event display
                $("."+la_class).removeClass("o_hidden");
            }else{
                $("."+la_class).addClass("o_hidden");
            }
            for (var sub in le_filter.child_filters) {
                le_sub = le_filter["child_filters"][sub];
                la_class = le_sub.class;
                if (le_sub.is_checked) {  // update event display
                    $("."+la_class).removeClass("o_hidden");
                }else{
                    $("."+la_class).addClass("o_hidden");
                }
            }
        }
    },
    /**
     *  Coche / décoche la case d'un filtre.
     *  Si on coche ou décoche un filtre parent, il faut le faire aussi pour les enfants
     *  Si on décoche le dernier sous-filtre coché, il faut décocher le filtre parent aussi
     *  Si on coche un filtre enfant alors qu'ils étaient tous décochés, il faut cocher le parent.
     *  Appelé par PlanningView.SidebarInfoFilter.on_click avec rebounce=true
     */
    do_toggle_checked: function (checked, filter_value, rebounce=false) {
        var le_filter, le_parent, la_class, la_input_sel;
        var ir_values_model = new Model('ir.values');

        if ( filter_value instanceof Array) {  // le filtre est un sous-filtre
            le_parent = this.info_filters[filter_value[0]];
            le_filter = le_parent["child_filters"][filter_value[1]];
            le_filter.is_checked = checked;  // update data

            if (rebounce) {
                // cocher le filtre parent si au moins un des sou-filtres est coché
                if (checked && !le_parent.is_checked) {
                    this.do_toggle_checked(true,filter_value[0],false);
                // décocher le filtre parent si tous les sous-
                }else if (this.all_subfilters_unchecked(filter_value[0]) && le_parent.is_checked) {
                    this.do_toggle_checked(false,filter_value[0],false);
                }
            }
        }else{  // le filtre est un filtre parent
            le_filter = this.info_filters[filter_value];
            le_filter.is_checked = checked;  // update data
            if (rebounce && !isNullOrUndef(this.info_filters[filter_value].child_filters)) {
                // appliquer le toggle aux enfants
                var le_tab = [];
                for (var k in le_filter.child_filters) {
                    le_tab = [filter_value, k];
                    this.do_toggle_checked(checked, le_tab, false);
                }
            }

        }
        // Appliquer le toggle à l'interface et enregistrer l'état des filtres
        la_class = le_filter.class;
        la_input_sel = "#"+le_filter.input_id;
        if (!isNullOrUndef(le_filter["field_name_ir"])) { // update config settings
            ir_values_model.call("set_default", ["of.intervention.settings", le_filter["field_name_ir"], checked, false]);
        }
        if (checked != $(la_input_sel).prop("checked")) { // update filter display
            $(la_input_sel).prop("checked", checked);
        }
        if (checked) {  // update event display
            $("."+la_class).removeClass("o_hidden");
        }else{
            $("."+la_class).addClass("o_hidden");
        }
    },
    /**
     *  Renvois true si tous les sous-filtres sont décochés
     */
    all_subfilters_unchecked: function (filter_value) {
        for (var k in this.info_filters[filter_value]["child_filters"]) {
            if (this.info_filters[filter_value]["child_filters"][k].is_checked) {
                return false;
            }
        }
        return true;
    },
    /**
     *  Handler pour le signal de click sur un filtre
     */
    on_click: function(e) {
        var la_value = e.target.value;
        var la_class;
        if (e.target.tagName == 'SPAN') {  // click sur span -> la checkboxe est a coté
            var la_input = e.target.previousElementSibling.firstElementChild;
            $("#"+la_input.id).click();
            return;
        }
        if (e.target.tagName == 'DIV') {  // click sur div
            // click sur div du filtre
            if (e.target.className == "of_planning_ev_info" || e.target.className.indexOf("of_planning_ev_subinfo") != -1) {
                $(e.target).find('input.' + e.target.className + '_input').click();
                return;
            }else{  // click sur div du widget
                return;
            }
        }
        if (e.target.tagName == 'I') {  // click sur i (montrer/cacher sous-filtres)
            for (var i=0; i<e.target.classList.length; i++) {
                if (e.target.classList[i].indexOf("of_planning_ev_info_toggle") != -1) {
                    $("." + e.target.classList[i]).toggleClass("o_hidden");
                    break;
                }
            }
            la_value = e.target.id.split("_");
            if (la_value[1] == "show") {
                $(".of_planning_ev_subinfo_" + la_value[0]).removeClass("o_hidden");
                // conserver l'état
                local_storage.setItem('planningview_info_filters_visible_' + la_value[0], true);
            }else{
                $(".of_planning_ev_subinfo_" + la_value[0]).addClass("o_hidden");
                // conserver l'état
                local_storage.setItem('planningview_info_filters_visible_' + la_value[0], false);
            }

            return;
        }
        var le_filter;
        if (la_value.indexOf("-") != -1) {  // le filtre est un sous-filtre
            la_value = la_value.split("-");
        }
        this.do_toggle_checked(e.target.checked, la_value, true);  // rebounce=true lors du premier appel
    },
    /**
     *  Handler pour le signal de click sur l'icône pour montrer les filtres
     */
    on_click_show_filters: function(e) {
        this.$(".of_planning_info_filter_show").addClass("o_hidden");
        this.$(".of_planning_info_filter_hide").removeClass("o_hidden");
        this.do_toggle_filters(true);
    },
    /**
     *  Handler pour le signal de click sur l'icône pour cacher les filtres
     */
    on_click_hide_filters: function(e) {
        this.$(".of_planning_info_filter_hide").addClass("o_hidden");
        this.$(".of_planning_info_filter_show").removeClass("o_hidden");
        this.do_toggle_filters(false);
    },
    /**
     *  Montrer / Cacher les filtres
     */
    do_toggle_filters: function(show) {
        if (show) {
            self.$('.of_planning_ev_infos').removeClass("o_hidden");
            this.info_filters_visible = true;
            // conserver l'état
            local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        }else{
            self.$('.of_planning_ev_infos').addClass("o_hidden");
            this.info_filters_visible = false;
            // conserver l'état
            local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        }
    },
});

var SidebarColorFilter = Widget.extend({
    events: {
        'click .of_color_filter': 'on_click',
    },
    /**
     *  called by Sidebar.start
     */
    init: function(parent, view) {
        this._super(parent,view);
        this.filters_radio = true;
        this.view = view;
        this.willStart();
        this.ready_to_render = $.Deferred();
    },
    willStart: function () {
        var self = this;
        this.dfd_color_filter = this.view.dataset.call("get_color_filter_data");
        return $.when(this.dfd_color_filter, this._super()).then(function (color_filter_data) {
            self.color_filter_data = color_filter_data;
            for (var k in color_filter_data) {
                if (color_filter_data[k].is_checked) {
                    self.current_radio_key = k;
                    break;
                }
            }
            self.ready_to_render.resolve()
        });
    },
    /**
     *  called by CalendarView._do_show_init
     */
    render: function () {
        var self = this;
        $.when(this.ready_to_render)
        .then(function (){
            return self.$el.html(qweb.render('CalendarView.sidebar.color_filter', { widget: self,
                                                                                    filters: self.color_filter_data,
                                                                                    filter_captions: self.color_filter_data })).promise();

        }).then(function() {
            return self.$el.insertAfter($(".of_planning_reso_filter"))
        });
    },
    /**
     *  Override of parent function. handles radio filters.
     */
    on_click: function(e) {
        var ir_values_model = new Model('ir.values');
        if (e.target.tagName !== 'INPUT') {
            $(e.currentTarget).find('input').click();
            return;
        }
        for(var key in this.color_filter_data){
            if (this.color_filter_data[key].field == e.target.value) {
                this.color_filter_data[key].is_checked = e.target.checked;
                this.current_radio_key = key;
                ir_values_model.call("set_default", ["of.intervention.settings",
                                                     "of_event_color_filter",
                                                     key, false]);
            }else{
                this.color_filter_data[key].is_checked = false;
            }
        };
        this.render();
        this.trigger_up('reload_events');
    },
});

var SidebarCaption = Widget.extend({
    /**
     *  Appelé par Sidebar.start
     */
    init: function(parent, view) {
        this._super(parent);
        this.view = view;
        this.start();
    },
    start: function() {
        this.$el.addClass("of_sidebar_element");
        return $.when(this._super());
    },
    /**
     *  Appelé par PlanningView.Sidebar.start
     */
    render: function () {
        var self = this;
        $.when(new Model(this.view.dataset.model).call('get_state_int_map'))
        .then(function (states){
            self.$el.html(qweb.render('CalendarView.sidebar.captions', { widget: self, captions: states }));
            self.do_show();
        });
    },
});

core.view_registry.add('planning', PlanningView);

return {
PlanningView: PlanningView,
PlanningRecord: PlanningRecord,
};
});
