odoo.define('of_timeline.TimelineView', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var Model = require('web.DataModel');
var View = require('web.View');
var Pager = require('web.Pager');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');
var ActionManager = require('web.ActionManager');
var map_controls = require('of_map_view.map_controls');
var map_utils = require('of_map_view.map_utils');
var Widget = require('web.Widget');
var QWeb = require('web.QWeb');
var mixins = core.mixins;
var formats = require('web.formats');
var time = require('web.time');
var local_storage = require('web.local_storage');

var CompoundDomain = data.CompoundDomain;

var _t = core._t;
var _lt = core._lt;
var qweb = core.qweb;

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

var MODE_COLUMN_NBS = {
    "day": 1,
    "week": 7,
    "month": 7,
};
/*
NEXT: action click creneau dispo on_close, nettoyage et commentaire du code
TODO:
*/
var PlanningView = View.extend({
    template: 'PlanningView',
    display_name: _lt('Planning'),
    icon: 'fa fa-sliders',
    searchview_hidden: true,
    view_type: "planning",
    _model: null,
    defaults: _.extend({}, View.prototype.defaults, {
        // records can be selected one by one
        selectable: true,
        // records can be deleted
        deletable: false,
        // whether the column headers should be displayed
        header: true,
        // display addition button, with that label
        addable: _lt("Create"),
        // whether the list view can be sorted, note that once a view has been
        // sorted it can not be reordered anymore
        sortable: false,
        // whether the view rows can be reordered (via vertical drag & drop)
        reorderable: true,
        action_buttons: true,
        // whether the editable property of the view has to be disabled
        disable_editable_mode: false,
        auto_search: false, // the search is done when the map is attached. See MapView.Map.on_map_attached. Apparently not taken into account D:
    }),
    events: {
        'click .of_planning_sidebar_toggler': 'toggle_full_width',
    },
    custom_events: {
        'all_rows_rendered': 'on_all_rows_rendered',
        'planning_record_open': 'open_record',
        //'planning_do_action': 'open_action',  // later implementation
        'reload_events': 'on_reload_events',
    },
    /**
     *
     */
    init: function (parent, dataset, view_id, options) {
        options['auto_search'] = false;
        this._super.apply(this, arguments);
        var attrs = this.fields_view.arch.attrs;
        if (!attrs.date_start) {
            throw new Error(_t("Planning view has not defined 'date_start' attribute."));
        }
        if (!attrs.resource) {
            throw new Error(_t("Planning view has not defined 'resource' attribute."));
        }
        for (var k in this.dataset.context) {
            if (k.indexOf("search_default") != -1) {
                delete this.dataset.context[k];
            }
        }
        this.dataset = new data.DataSetSearch(this.ViewManager.action_manager, 'of.planning.intervention', this.dataset.context, [])
        this.resource = attrs.resource;
        this.color_ft = attrs.color_ft;
        this.color_bg = attrs.color_bg;
        this.fields = this.fields_view.fields;
        this.fields_keys = _.keys(this.fields_view.fields);
        this.name = this.fields_view.name || attrs.string;
        this.rows = {}; // dict of events {id1: [ev1,ev2], id2: [ev3], ..}

        this.date_start = attrs.date_start;     // Field name of starting date field
        this.date_delay = attrs.date_delay;     // duration
        this.date_stop = attrs.date_stop;
        this.all_day = attrs.all_day;

        this.mode = attrs.mode || options.mode || "week";  // Just week for now. Later one of month, week or day.
        this.column_nb = MODE_COLUMN_NBS[this.mode];
        this.range_start = moment().startOf(this.mode)._d;
        this.range_stop = moment().endOf(this.mode)._d;
        this.planning_table = false;
        this.set_columns();

        this.shown = $.Deferred();

        this.info_fields = [];
        for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
            if (isNullOrUndef(this.fields_view.arch.children[fld].attrs.invisible)) {
                this.info_fields.push(this.fields_view.arch.children[fld].attrs.name); // don't add field to description if invisible="1"
            }
        }

        this.first_search_done = false;
        // debounce des handlers de click pour éviter le multiclick
        this.on_today_clicked = _.debounce(this.on_today_clicked, 300, true);
        this.on_next_clicked = _.debounce(this.on_next_clicked, 300, true);
        this.on_prev_clicked = _.debounce(this.on_prev_clicked, 300, true);
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
        var excluded_ids_def = new Model("ir.values").call("get_default", ["of.intervention.settings", "planningview_employee_exclu_ids"]);
        var intervenants_ids_def = new Model("hr.employee").query(['id']) // retrieve ids from db
            .filter([['of_est_intervenant', '=', true]]) // seulement les intervenants
            .all();  // récupérer tous les employés qui sont des intervenants
        var ir_values_model = new Model("ir.values");
        // récupérer la dernière semaine affichée en vue planning pour l'utilisateur en cours -> inhibé pour l'instant
        //var range_start_def = ir_values_model.call("get_default", ["of.intervention.settings", "planningview_range_start", false]);
        // initialiser les couleurs des créneaux dispo et leur durée minimale
        var creneaux_dispo_data_def = self.set_creneaux_dispo_data();

        return $.when(write_def, create_def, excluded_ids_def, intervenants_ids_def, rendered_prom, creneaux_dispo_data_def, this._super()).then(
            function (write, create, excluded, emp_ids) {
                self.write_right = write;
                self.create_right = create;
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
                /*if (!isNullOrUndef(range_start)) {  // saut à la dernière semaine consultée si existante
                    self.range_start = moment.utc(range_start).local().startOf(self.mode)._d;
                    self.range_stop = moment.utc(range_start).local().endOf(self.mode)._d;
                }*/
                // initialiser les filtres grâce à la liste des intervenants à montrer en vue planning
                var all_filters_def = self._set_all_custom_colors();

                return $.when(all_filters_def);
        });
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
     *  called by PlanningView.willStart
     *  initialise this.all_filters
     */
    _set_all_custom_colors: function() {
        var self = this;
        var ids = _.reject(_.keys(self.all_filters),function(num){ return num == 'undefined'; });

        var dfd = $.Deferred();
        var dfd2 = $.Deferred();
        var p = dfd.promise({target: kays});
        var p2 = dfd2.promise();
        var kays = [];
        var model_name = self.fields[self.resource].relation;
        var Attendees = new Model(model_name);

        Attendees.query(['id', self.color_ft, self.color_bg, 'name']) // retrieve colors from db
            .filter([['id', 'in', self.view_res_ids || []]]) // id
            .all()
            .then(function (attendees){
                self.all_filters = {};
                for (var i=0; i<attendees.length; i++) {
                    var a = attendees[i];
                    var key = a.id;
                    kays.push(key);
                    var filter_item = {
                        label: a['name'],
                        color_bg: a[self.color_bg],
                        color_ft: a[self.color_ft],
                        value: a['id'],
                        input_id: a['id'] + "_input",
                        is_checked: true,
                    }
                    self.all_filters[key] = filter_item;
                };
                dfd.resolve();
                var ir_values_model = new Model("ir.values");
                // récupérer la sélection (coché/décoché) des filtres de la dernière utilisation de la vue planning
                ir_values_model.call("get_default", ["of.intervention.settings", "planningview_filter_intervenant_ids", false])
                .then(function (attendee_ids) {
                    if (typeof attendee_ids == "string") {  // transformer en tableau si besoin
                        attendee_ids = JSON.parse(attendee_ids)
                    }
                    // tout cocher si tout était décoché
                    if (isNullOrUndef(attendee_ids) || attendee_ids.length == 0) {
                        self.filter_attendee_ids = []
                        for (var k in self.all_filters) {
                            self.filter_attendee_ids.push(self.all_filters[k].value);
                        };
                    // code 6: [(6, 0 [ids])]
                    }else if (attendee_ids[0].length == 3 && attendee_ids[0][0] == 6 && !attendee_ids[0][1]) {
                        self.filter_attendee_ids = attendee_ids[0][2];
                    // liste d'identifiants
                    }else{
                        self.filter_attendee_ids = attendee_ids;
                        var idf;
                        var found;
                        // décocher les filtres qui ne sont pas dans attendee_ids //@totest: nécessaire?
                        for (var k in self.all_filters) {
                            found = false;
                            idf = self.all_filters[k].value;
                            for (var j in attendee_ids) {
                                if (attendee_ids[j] == idf) {
                                    found = true;
                                }
                            }
                            if (!found) {
                                self.all_filters[k].is_checked = false;
                            }
                        };
                    }
                    dfd2.resolve();
                });
            });

        return $.when(p, p2).then(function(){
            return kays;
        });
    },
    /**
     *
     */
    start: function () {
        // raccourcis jquery
        this.$sidebar_container = this.$(".of_planning_sidebar_container");  // Panneau latéral droit
        this.$table_container = this.$(".of_planning_table_container");  // Contenu de la vue
        this.$el.addClass(this.fields_view.arch.attrs.class);
        this.shown.done(this.init_table.bind(this));
        return this._super();
    },
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
                //dateFormat: le_dateFormat.toLowerCase(),
            });

            defs.push(this.extraSideBar());

            // Add show/hide button and possibly hide the sidebar
            this.$sidebar_container.append($('<i>').addClass('of_planning_sidebar_toggler fa'));
            this.toggle_sidebar((local_storage.getItem('planning_view_full_width') !== 'true'));
        }
        return $.when.apply($, defs)
        .then(function () {
            self.table_inited = true;
            self.do_search(this.domain,this.context,this.group_by);
        });
    },
    calendarMiniChanged: function (context) {
        return function(datum,obj) {
            var curMode = context.mode;
            var curDate = new Date(obj.currentYear , obj.currentMonth, obj.currentDay);

            if (curMode == "week") {
                if (curDate <= context.range_stop && curDate >= context.range_start) {  // day of same week
                    //console.log("that doesn't do anything...")
                }else{
                    context.range_start = moment(curDate).startOf("week")._d;
                    context.range_stop = moment(curDate).endOf("week")._d;
                    context.do_search(context.domain,context.context,context.group_by);
                }
            }
        };
    },
    extraSideBar: function() {
        return $.when();
    },
    toggle_full_width: function () {
        var full_width = (local_storage.getItem('planning_view_full_width') !== 'true');
        local_storage.setItem('planning_view_full_width', full_width);
        this.toggle_sidebar(!full_width);
    },
    toggle_sidebar: function (display) {
        this.sidebar.do_toggle(display);
        this.$('.of_planning_sidebar_toggler')
            .toggleClass('fa-close', display)
            .toggleClass('fa-chevron-left', !display)
            .attr('title', display ? _('Close Sidebar') : _('Open Sidebar'));
        this.$sidebar_container.toggleClass('of_sidebar_hidden', !display);
    },
    do_search: function (domain, context, group_by) {
        var self = this;
        var context_dfd, domain_dfd, range_start_dfd = $.Deferred();
        var ir_values_model = new Model('ir.values');
        // 1ère recherche: on charge la config, autres recherches, on affecte la config inhibé pour l'instant
        /*if (!this.first_search_done) {
            range_start_dfd = $.when();
        }else{
            var format = time.datetime_to_str;
            var range_start_str = format(this.range_start);
            range_start_dfd = ir_values_model.call("set_default", ["of.intervention.settings", "planningview_range_start", range_start_str, false]);
        }*/
        this.domain = [];
        this.context = context;
        this.group_by = group_by;

        //$.when(range_start_dfd).then(function(){
        if (self.table_inited && self.first_search_done) {
            self._do_search(self.domain, self.context, self.group_by);
        }else{
            self.first_search_done = true;
            console.log('do_search not done, planning view not inited');
        }
        //})

    },
    _do_search: function(domain, context, group_by) {
        var self = this;
        var la_key;
        if (! self.all_filters) {
            self.all_filters = {};
        }
        self.rows = {};
        var row_options, emp_id;
        for (var i in self.view_res_ids) {
            emp_id = self.view_res_ids[i];
            row_options = {
                "res_id": emp_id,
                "auto_render": false,
            }

            self.rows[emp_id] = new PlanningView.Row(self.table,self,[],row_options);
            self.rows[emp_id].head_column = self.all_filters[emp_id].label;
        }
        self.col_offset_today = null;
        if (moment(self.range_start) <= moment() && moment() <= moment(self.range_stop)) {
            self.col_offset_today = moment().startOf('day').diff(moment(self.range_start), 'days');
        }
        var event_domain = self.get_range_domain([],this.range_start,this.range_stop);  // retrait du domain de recherche

        self.dataset.read_slice(self.fields_keys, {
                    offset: 0,
                    domain: event_domain,
                    context: context,
            }).done(function(events) {
                self.now_filter_ids = self.view_res_ids;  //hack for testing not to rewrite all the code

                self.set_columns();
                if (events.length >0) {
                   //console.log("events: ",events,self.fields_keys);

                    var filter_item;
                    var event, planning_record, day_span, col_offset_start, col_offset_stop, record_options, row_options, event_res_ids, res_id;
                    for (var i=0; i<events.length; i++) {
                        event = events[i];
                        event_res_ids = event[self.resource];
                        // how many days?
                        day_span = moment(event[self.date_stop]).startOf('day').diff(moment(event[self.date_start]).startOf('day'), 'days')+1;
                        if (day_span > 1) {
                            col_offset_stop = moment(event[self.date_stop]).startOf('day').diff(moment(self.range_start), 'days');
                            //col_offset_stop = Math.min(col_offset_stop,6);
                        }else{
                            col_offset_stop = undefined;
                        }
                        // the column index to insert the record
                        col_offset_start = moment(event[self.date_start]).startOf('day').diff(moment(self.range_start), 'days');
                        if (col_offset_start < 0) {
                           //console.log("TROP TOT")
                        }else if (col_offset_start >= self.column_nb) {
                           //console.log("TROP TARD");
                        }
                        record_options = {
                            "col_offset_start": col_offset_start,
                            "col_offset_stop": col_offset_stop,
                            "day_span": day_span,
                        }

                        for (var j in event_res_ids) {
                            res_id = event_res_ids[j];
                            if (_.contains(self.view_res_ids, res_id)) {  // don't the one from employees not to be shown
                                planning_record = new PlanningRecord(self.rows[res_id],self,event,record_options);
                                self.rows[res_id]["records_to_add"].push(planning_record);
                            }
                        }
                    }
                }

                // initialiser les segments horaires, les fillerbars, les créneaux dispos et les couleurs des employés
                var prom = self.set_res_horaires_data();
                $.when(prom).then(function () {
                    if (self.sidebar) {
                        self.sidebar.reso_filter.render();
                        //console.log("self.now_filter_ids:",self.now_filter_ids);
                        for (var key in self.rows) {
                            var key_num = Number(key);
                            if (self.all_filters[key_num].is_checked) {
                                self.rows[key].hidden = false;
                            }else{
                                self.rows[key].hidden = true;
                            }
                        }
                    }
                    var rgb, rgb_today;
                    for (var key in self.rows) {
                        self.rows[key].segments_horaires = self.res_horaires_info[key]['segments'];
                        self.rows[key].col_offset_to_segment = self.res_horaires_info[key]['col_offset_to_segment'];
                        self.rows[key].fillerbars = self.res_horaires_info[key]['fillerbars'];
                        self.rows[key].creneaux_dispo = self.res_horaires_info[key]['creneaux_dispo'];
                        self.rows[key].color_bg = self.res_horaires_info[key]['color_bg'];
                        self.rows[key].color_ft = self.res_horaires_info[key]['color_ft'];
                        rgb = hexToRgb(self.res_horaires_info[key]['color_bg']);
                        self.rows[key].color_bg_rgba = "rgba(" + rgb.r + "," + rgb.g + "," + rgb.b + ",0.3);";
                        self.rows[key].col_offset_today = isNullOrUndef(self.col_offset_today) ? -1 : self.col_offset_today;
                        if (self.rows[key].col_offset_today != -1) {
                            rgb_today = hexToRgb(self.res_horaires_info[key]['color_bg'], -30);
                            self.rows[key].color_bg_rgba_today = "rgba(" + rgb_today.r + "," + rgb_today.g + "," + rgb_today.b + ",0.4);";
                        }
                    }

                    self.table.rows = self.rows;
                    self.render_table();
                })
            });
    },
    set_res_horaires_data: function(res_ids=false, start=false, end=false, get_segments=false) {
        var self = this;
        var dfd = $.Deferred();
        var p = dfd.promise()
        res_ids = res_ids || self.view_res_ids;
        start = start || self.range_start;
        end = end || self.range_stop;

        var Planning = new Model(self.model);
        Planning.call('get_emp_horaires_info', [res_ids, start, end, get_segments])
        .then(function (result) {
            //console.log("result",result);
            if (isNullOrUndef(self.res_horaires_info)) {
                self.res_horaires_info = result;
            }else{
                for (var i=0; i<res_ids.length; i++) {
                    self.res_horaires_info[res_ids[i]] = result[res_ids[i]];
                }
            }

            dfd.resolve();
        });
        return $.when(p);
    },
    /**
     *  Adds custom colors to filters.
     *  called by SidebarResoFilter.render()
     */
    get_all_filters_ordered: function() {
        var self = this
        var filters = _.values(this.all_filters);
        return filters;
    },
    /**
     *  Renders the table then each of its rows
     */
    render_table: function() {
        var self = this;
       //console.log("render_table");
        var rendered_prom = this.$(".of_planning_table").html(qweb.render("PlanningView.table", {"table": this.table})).appendTo(self.$table_container).promise();

        return $.when(rendered_prom)
            .then(function () {  // render rows
                _.each(self.rows, function(row) {
                    row.render();
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
       //console.log("RENDER BUTTONS");
        var self = this;
        this.$buttons = $(qweb.render("PlanningView.buttons", {'widget': this}));
        this.$buttons.on('click', 'button.of_planning_button_new', function () {
            self.dataset.index = null;
            self.do_switch_view('form');
        });
        //

        this.$buttons.find(".of_planning_button_prev").click(
            this.proxy(self.on_prev_clicked));
        this.$buttons.find(".of_planning_button_today").click(
            this.proxy(self.on_today_clicked));
        this.$buttons.find(".of_planning_button_next").click(
            this.proxy(self.on_next_clicked));
        // modes are for later implementation...
        /*this.$buttons.find(".of_planning_button_day").click(
            this.proxy(self.on_scale_day_clicked));*/
        /*this.$buttons.find(".of_planning_button_week").click(
            this.proxy(self.on_scale_week_clicked));
        /*this.$buttons.find(".of_planning_button_month").click(
            this.proxy(self.on_scale_month_clicked));*/

        //this.$buttons.find('.of_planning_button_scale_' + this.mode).toggleClass("btn-primary btn-default");

        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            this.$('.of_planning_buttons').replaceWith(this.$buttons);
        }
    },/**/
    /**
     *  mode switching
     */
    on_prev_clicked: function (ev) {
       //console.log("on_prev_clicked!",ev);
        this.range_stop = moment(this.range_start).subtract(1, 'hours').endOf(this.mode)._d;
        this.range_start = moment(this.range_start).subtract(1, 'hours').startOf(this.mode)._d;
       //console.log("le moment: ",)
        this.$small_calendar.datepicker("setDate",moment(this.range_start).format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    on_today_clicked: function(ev) {
       //console.log("on_today_clicked!",ev);
        this.range_start = moment().startOf(this.mode)._d;
        this.range_stop = moment().endOf(this.mode)._d;
        this.$small_calendar.datepicker("setDate",moment().format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    on_next_clicked: function (ev) {
       //console.log("on_next_clicked!",ev);
        this.range_start = moment(this.range_stop).add(1, 'hours').startOf(this.mode)._d;
        this.range_stop = moment(this.range_stop).add(1, 'hours').endOf(this.mode)._d;
        this.$small_calendar.datepicker("setDate",moment(this.range_start).format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    /**
     *  for later implementation
     */
    on_scale_day_clicked: function(ev) {
       //console.log("on_scale_day_clicked!",ev);
        if (this.mode != "day") {
            this.$buttons.find('.of_planning_button_' + this.mode).toggleClass("btn-primary btn-default");
            this.$buttons.find('.of_planning_button_day').toggleClass("btn-primary btn-default");
            this.do_switch_mode("day");
        }
    },
    /**
     *  for later implementation
     */
    on_scale_week_clicked: function(ev) {
       //console.log("on_scale_week_clicked!",ev);
        if (this.mode != "week") {
            this.$buttons.find('.of_planning_button_' + this.mode).toggleClass("btn-primary btn-default");
            this.$buttons.find('.of_planning_button_week').toggleClass("btn-primary btn-default");
            this.do_switch_mode("week");
        }
    },
    /**
     *  for later implementation
     */
    on_scale_month_clicked: function(ev) {
       //console.log("on_scale_month_clicked!",ev);
        if (this.mode != "month") {
            this.$buttons.find('.of_planning_button_' + this.mode).toggleClass("btn-primary btn-default");
            this.$buttons.find('.of_planning_button_month').toggleClass("btn-primary btn-default");
            this.do_switch_mode("month");
        }
    },
    /**
     *  for later implementation
     */
    do_switch_mode: function(new_mode) {
       //console.log("do_switch_mode: ",this.mode,new_mode);
        this.mode = new_mode;
        this.column_nb = MODE_COLUMN_NBS[this.mode];
        this.range_start = moment().startOf(this.mode)._d;
        this.range_stop = moment().endOf(this.mode)._d;
        //this.do_search(this.domain,this.context,this.group_by);
    },
    /**
     *  Handles signal that all rows are rendered
     */
    on_all_rows_rendered: function() {
        if (this.sidebar) {
            if (this.sidebar.info_filter.rendered) {
               //console.log("ALREADY RENDERED!");
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
        //event_domain = new CompoundDomain(event_domain, ['id', '=', res_id]);
        //console.log("event_domain",event_domain);
        this.rows[res_id].clear_column(column);
        this.dataset.read_slice(this.fields_keys, {offset: 0, domain: event_domain, context: self.context,
        }).done(function(events) {
            if (events.length >0) {
               //console.log("events: ",events,self.fields_keys);

                var event, planning_record, day_span, col_offset_start, col_offset_stop, record_options, row_options, event_res_ids;
                for (var i=0; i<events.length; i++) {
                    //console.log(i,events.length);
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
                    //console.log("EVENT:",event);
                    //console.log("DAY SPAN:",day_span);
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
                    //console.log("duration: ",day_span);
                    
                    record_options = {
                        "col_offset_start": col_offset_start,
                        "col_offset_stop": col_offset_stop,
                        //"color_bg": event[self.color_bg] || "#7FFF00",
                        //"color_ft": event[self.color_ft] || "#0C0C0C",
                        "day_span": day_span,
                    }
                    //console.log("col_offset_start: ",col_offset_start);

                    //console.log("event: ",event);
                    //self.view_res_ids = _.union(self.view_res_ids, event_res_ids);
                    //console.log("self.res_ids",self.res_ids);
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
                            //console.log("PLANNING_ROECORD",planning_record);
                            self.rows[res_id] = new PlanningView.Row(self.table,self,[],row_options);
                        }* /
                        //console.log("WEUT");

                        planning_record = new PlanningRecord(self.rows[res_id],self,event,record_options);
                        self.rows[res_id]["records_to_add"].push(planning_record);
                    //}
                }
            }
            //console.log("res_id", res_id, typeof(res_id));
            //console.log("self.res_horaires_info",self.res_horaires_info);
            var prom = self.set_res_horaires_data([res_id], date_column, date_fin, self.res_horaires_info[res_id].segments_horaires);
            $.when(prom).then(function () {
                self.rows[res_id].fillerbars[column] = self.res_horaires_info[res_id]['fillerbars'][0];
                self.rows[res_id].creneaux_dispo[column] = self.res_horaires_info[res_id]['creneaux_dispo'][0];
                self.rows[res_id].render(column);
            });
        });
    },*/
    open_record: function (event, options) {
        var self = this;
        var additional_context = {};
        var action_id = "of_planning.action_of_planning_intervention_form"

        return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
                //console.log("LE RESUUUULT",result);
                //result.target = "new"; -> inhibé pour avoir accès aux actions
                result.res_id = event.data.id;
                var options = {
                    'additional_context': pyeval.eval('context', additional_context),  // pour une raison inconnue le additional_context n'est pas pris en compte avant
                    'on_close': function () {self.trigger_up('reload_events')},
                };  // @todo: appel reload_events
                //return self.view.ViewManager.action_manager.ir_actions_act_window(result,options);
                return self.ViewManager.action_manager.do_action(result,options);
            });
    },
    /** For later implementation
     *  Handles signal to open an action
     * /
    open_action: function (event) {
        var self = this;
        //if (event.data.context) {
            event.data.context = new data.CompoundContext(event.data.context)
                .set_eval_context({
                    active_id: 2,//event.target.id,
                    active_ids: [2],//[event.target.id],
                    active_model: this.model,
                });
        //}
       //console.log("EXECUTE ACTION!",event.data, this.dataset, event.target.id, function(){return});
        //console.log("event data:",event.data);   event.target.id
        this.do_execute_action(event.data, this.dataset, undefined, function(){return})//_.bind(self.reload_record, this, event.target));
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
     * Build OpenERP Domain to filter object by this.date_start and this.date_stop field
     * between given start, end dates.
     */
    get_range_domain: function(domain, start, end, res_ids) {
        var format = time.datetime_to_str;
        res_ids = res_ids || this.view_res_ids;
        var extend_domain = [[this.date_start, '<=', format(end)]];
        if (this.date_stop) {
            extend_domain.push([this.date_stop, '>=', format(start)]);
        } else if (!this.date_delay) {
            extend_domain.push([this.date_start, '>=', format(start)]);
        }
        extend_domain.push(['employee_ids', 'in', res_ids]);
        return new CompoundDomain(domain, extend_domain);
    },
});

PlanningView.Table = Widget.extend({
    template: "PlanningView.table",
    custom_events: {
        'row_rendered': 'on_row_rendered',
    },
    init: function(parent, options) {
       //console.log("PlanningView.Table init args: ",arguments);
        this._super.apply(this, arguments);
        this.view = parent;
        this.columns = this.view.columns;
        this.head_column = this.view.head_column;
        this.rows = this.view.rows;
        this.appendTo(this.view.$table_container);
        //this.willStart();
    },
    /**
     *
     */
    start: function () {
       //console.log("START PlanningView.Table");
        this.$tbody = this.$("tbody");
       //console.log("TBODY LEN:",this.$tbody.length);
        return this._super();
    },
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(qweb.render(this.template, {table: this}).trim());
        } else {
            $el = this._make_descriptive();
        }
        this.replaceElement($el);
    },
    on_row_rendered: function() {
        if (this.check_all_rows_rendered()) {
            this.trigger_up("all_rows_rendered");
        }
    },
    check_all_rows_rendered: function() {
        for (var k in this.rows) {
            if (!this.rows[k].rendered) {
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
       //console.log("PlanningView.Row init args: ",arguments);
        this._super.apply(this, arguments);
        this.options = options;
        // couleurs affectées dans le _do_search de la vue
        //this.color_bg = options.color_bg;
        //var le_rgb = hexToRgb(this.color_bg);
        //this.color_bg_rgba = "rgba(" + le_rgb.r + "," + le_rgb.g + "," + le_rgb.b + ",0.3);"
        //this.color_ft = options.color_ft;
        this.res_id = options.res_id;
        this.id = "of_planning_row_" + this.res_id;
        this.hidden = options.hidden || false;
        this.table = view.table;
        this.view = view;
        this.fillerbar_color_dispo = view.creneaux_dispo.color_bg;
        this.model = new Model(this.view.fields[this.view.resource].relation);
        this.head_column = this.options.head_column;
        this.column_nb = this.view.column_nb;
        this.columns = new Array(this.column_nb);
        this.fillerbars = [];//new Array(this.column_nb);
        this.records_multiples = {};
        this.records_to_add = [];
        this.records_added = [];
        for (var i=0; i<this.columns.length; i++) {
            this.columns[i] = [];
        }
        self.dfd_horaires = $.Deferred();
        self.ready_to_render = $.Deferred();
    },
    /**
     *  col_index optionnal, keep undefined for rendering all columns
     */
    render: function (col_index) {
        var self = this;

        var le_model = new Model("of.planning.intervention");
        var fillerbarzz = [];
        self.assing_records_to_columns();
        $.when(self.ready_to_render).then(function(){

            var $la_row = self.table.$('#'+self.id);
            if ($la_row.length >0) {
               //console.log("FOUND",self.$el);
                return self.replace($la_row);
            }


            var le_creneau, found, la_len;
            var descript_dt = {type: "datetime"};
            var descript_ft = {type: "float_time"};
            var formatted_heure_record, formatted_heure_creneau;
            var options = {};
            //console.log(self.res_id, self.creneaux_dispo)
            if (!self.creneaux_dispo.length) {// == []) {
                self.zero_horaire = true;
            }else{
                self.zero_horaire = false;
                for (var i=0; i<7; i++) {
                    options = {col_offset: i};
                    if (isNullOrUndef(col_index) || i==col_index) {
                        for (var j=0; j<self.creneaux_dispo[i].length; j++) {

                            le_creneau = new PlanningCreneauDispo(self, self.view, self.creneaux_dispo[i][j], options);
                            self.columns[i].push(le_creneau);
                            function compareFunction(recA, recB) {
                                var heure_debut_a = recA.heure_debut,
                                    heure_debut_b = recB.heure_debut;
                                if (!isNullOrUndef(recA.hours_cols)) {
                                    heure_debut_a = recA.hours_cols[i].heure_debut;
                                }
                                if (!isNullOrUndef(recB.hours_cols)) {
                                    heure_debut_b = recB.hours_cols[i].heure_debut;
                                }
                                return heure_debut_a - heure_debut_b;
                            }
                            self.columns[i].sort(compareFunction);
                            //_.sortBy(self.columns[i], 'heure_debut');  // @TODO: gerer asynchronicité
                        }
                    }
                }
            }
           //console.log("self.COLUMNS!",self.columns);
           //console.log("self.FILLERBARS!",self.fillerbars);
           //console.log("self.DISPOOO!",self.creneaux_dispo);
            return $.when()
        })
        .then(function () {  // rendering
            if (isNullOrUndef(col_index)) {
                return self.$el.html(qweb.render(self.template, {"row": self})).promise()
            }else{
                var $column = $(".of_planning_td_" + self.res_id + "_" + col_index);
                //if (!$column.length) console.log("WEUT?");
                return $column.html(qweb.render('PlanningView.row.column', { "col_index": col_index , "row": self,})).promise();
            }
        })
        .then(function (a_ver) {
            //console.log("a ver",a_ver);
            self.$el.attr("id", self.id);
            self.rendered = true;
            if (self.hidden) {
                self.do_hide();
            }
            var $fillerbar, fillerbar, tooltip_options, fil_title;
            tooltip_options = {
                delay: { show: 501, hide: 0 },
                title: "Cet intervenant travaille plus d'heures que son maximum pour cette journée",
            }
            self.$(".of_planning_fillerbar_warning").tooltip(tooltip_options);
            if (!self.zero_horaire) {
                for (var i=0; i<7; i++) {
                    if (isNullOrUndef(col_index) || col_index==i) {
                        $fillerbar = self.$("#of_planning_fillerbar_" + self.res_id + "_" + i);
                        fillerbar = self.fillerbars[i];
                        //console.log("LA FILLERBAR!", fillerbar);

                        if (!fillerbar.nb_heures_travaillees) {
                            fil_title = "Journée non travaillée"
                        }else{
                            fil_title = "Horaires du jour: " + fillerbar["creneaux_du_jour"] + "<br/>"
                            + fillerbar["heures_occupees_str"] + " occupées sur "
                            + fillerbar["heures_travaillees_str"] + " travaillées (" + fillerbar["pct_occupe"].toFixed(2) + "%)"
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
        .then(function () {
            for (var i=0; i<7; i++) {
                if (isNullOrUndef(col_index) || col_index==i) {
                    for (var j=0; j<self.columns[i].length; j++) {
                        // res_id, col_index
                        self.columns[i][j].render(i);
                    }
                }
            }
            self.trigger_up("row_rendered")
        });
    },
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(qweb.render(this.template, {row: this}).trim());
        } else {
            $el = this._make_descriptive();
        }
        this.replaceElement($el);
    },
    clear_column: function (column) {
        var record;
        while (this.columns[column].length) {
            record = this.columns[column].pop();
            record.destroy();
        }
    },
    /**
     *
     */
    add_record: function (planning_record) {
        var self = this;
        if (isNullOrUndef(planning_record.col_offset_start)) {
           //console.log("ERREUR: col_offset_start manquant",planning_record);
        }else if(isNullOrUndef(planning_record.col_offset_stop)) {  // 1 day event
            //console.log("ONE DAY EV COL",planning_record.col_offset_start,planning_record);
            self.columns[planning_record.col_offset_start].push(planning_record);
            self.records_added.push(planning_record)
            self.trigger_up("record_added");
        }else{  // several days event: get the actual hours to display (exple: 17:00 -> 18:00 and 9:00 -> 11:30 in place of twice 17:00 -> 11:30) smoother to display and to sort
            //console.log("PLANNING RECORD SEVDAYS:",planning_record);
            self.records_multiples[planning_record.id] = [];
            planning_record["hours_cols"] = {};
            planning_record.$of_el = {};
            var a_push, horaires_dict;
            var descript_ft = {type: "float_time"};
            // assign start and end hours to multiple day records, not completely accurate still
            for (var i=planning_record.col_offset_start; i<=planning_record.col_offset_stop; i++) {
                a_push = true;

                if (i>=0 && i<self.column_nb) {
                    planning_record.$of_el[i] = planning_record.$el.clone(true);
                    horaires_dict = self.segments_horaires[self.col_offset_to_segment[i]][2];  // récupérer le bon horaires_dict
                    //console.log("pushed to column ",i);
                    //console.log("horaires_dict",horaires_dict);
                    planning_record["hours_cols"][i] = {};
                    if (i == planning_record.col_offset_start) {  // first day
                        if ( isNullOrUndef(horaires_dict[i + 1]) || horaires_dict[i + 1].length == 0 ) {  // jour non travaillé. peut arriver pour une intervention de plusieurs jours qui commence le dimanche
                            planning_record["hours_cols"][i].heure_debut = false;
                            planning_record["hours_cols"][i].heure_fin = false;
                            a_push = false;
                        }else{
                            planning_record["hours_cols"][i].heure_debut = planning_record.heure_debut;
                            planning_record["hours_cols"][i].heure_fin = horaires_dict[i+1][horaires_dict[i+1].length-1][1]  // heure de fin du dernier créneau du jour

                        }
                    }else if (i >= planning_record.col_offset_start && i < planning_record.col_offset_stop) {
                        if ( isNullOrUndef(horaires_dict[i + 1]) || horaires_dict[i + 1].length == 0 ) {  // jour non travaillé
                           //console.log("jour non travaillé pour ",self.res_id);
                           //console.log("i",i);
                            planning_record["hours_cols"][i].heure_debut = false;
                            planning_record["hours_cols"][i].heure_fin = false;
                            a_push = false;
                        }else{
                            planning_record["hours_cols"][i].heure_debut = horaires_dict[i+1][0][0]  // heure de début du premier créneau du jour
                            planning_record["hours_cols"][i].heure_fin = horaires_dict[i+1][horaires_dict[i+1].length-1][1]  // heure de fin du dernier créneau du jour
                        }
                    }else if (i == planning_record.col_offset_stop) {  // last day
                        if ( isNullOrUndef(horaires_dict[i + 1]) || horaires_dict[i + 1].length == 0 ) {  // jour non travaillé. peut arriver pour une intervention de plusieurs jours qui termine la semaine suivante
                            planning_record["hours_cols"][i].heure_debut = false;
                            planning_record["hours_cols"][i].heure_fin = false;
                            a_push = false;
                        }else{
                            planning_record["hours_cols"][i].heure_debut = horaires_dict[i+1][0][0]  // heure de début du premier créneau du jour
                            planning_record["hours_cols"][i].heure_fin = planning_record.heure_fin;
                        }
                    }
                    //console.log("HOURS COLS",planning_record["record"],planning_record["hours_cols"]);
                    planning_record["hours_cols"][i].heure_debut_str = formats.format_value(planning_record["hours_cols"][i].heure_debut,descript_ft);
                    planning_record["hours_cols"][i].heure_fin_str = formats.format_value(planning_record["hours_cols"][i].heure_fin,descript_ft);
                    var duree_col = planning_record["hours_cols"][i].heure_fin - planning_record["hours_cols"][i].heure_debut
                    planning_record["hours_cols"][i].duree = duree_col
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
     *  appelée dans render()
     */
    assing_records_to_columns: function () {
        var record_to_add;
        if (this.records_to_add.length == 0) {
            this.ready_to_render.resolve();
        }
        for (var i in this.records_to_add) {
            record_to_add = this.records_to_add[i];
            this.add_record(record_to_add);
        }
    },
    /**
     *
     */
    on_record_added: function (ev) {
        if (this.records_to_add.length == this.records_added.length) {
            this.on_all_records_added()
        };
    },
    /**
     *
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
    },
    init: function(row, view, record, options) {
        this._super(row);
        this.row = row;
        this.view = view;
        this.options = options;
        this.color_bg = this.view.creneaux_dispo.color_bg;
        this.color_ft = this.view.creneaux_dispo.color_ft;
        this.col_offset = options.col_offset;

        this.minimized = false;  // à voir si supprimer
        this.type = "disponible";  // à voir si supprimer

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
        //console.log("LES CRENEAUX REELS", this.creneaux_reels)
        this.secteur_id = record.secteur_id;
        this.secteur_str = record.secteur_str;
        this.display_secteur = record.display_secteur;
        var heures = Math.trunc(this.duree);
        var minutes = (this.duree - heures) * 60;
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

        this.date = moment(this.view.range_start).add(self.col_offset, 'days').format('YYYY-MM-DD'),
        this.lieu_debut = record.lieu_debut;
        this.lieu_fin = record.lieu_fin;

        // inhiber double-clique
        this.on_planning_creneau_secteur_action_clicked = _.debounce(this.on_planning_creneau_secteur_action_clicked, 300, true);
        this.on_planning_creneau_action_clicked = _.debounce(this.on_planning_creneau_action_clicked, 300, true);
    },
    /**
     *  génère le rendu visuel du créneau et l'attache à la colonne correspondante
     */
    render: function(col_index) {
        var self = this;
        if (isNullOrUndef(col_index)) {
            col_index = self.col_offset;
        }
        return self.$el.html(qweb.render('PlanningView.creneau_dispo', {"creneau": self, "col_index": col_index})).promise()
            .then(function (){
                var td_id = "of_planning_td_" + self.row.res_id + "_" + col_index;
                self.$el.appendTo("#" + td_id);
            })
    },
    /**
     *  reloads, rerenders. after selecting a secteur
     */
    reload_secteur: function() {
        var self = this;
        var tournee_mod = new Model("of.planning.tournee")
        return tournee_mod.query(['id', 'employee_id', 'date', 'secteur_id']) // retrieve secteur from db
            .filter([['employee_id','=', self.row.res_id], ['date','=', self.date]]) // id
            .limit(1)
            .all()
            .then(function (result){
                //console.log("result tournee", result);
                if (result.length == 1) {
                    if (!result[0].secteur_id) {
                        self.secteur_id = false;
                        self.secteur_str = "";
                    }else{
                        self.secteur_id = result[0].secteur_id[0];
                        self.secteur_str = result[0].secteur_id[1];
                    }
                }
                return self.render();
            });
    },
    /**
     *  reloads all events
     */
    reload_events: function () {
        this.trigger_up('reload_events');
    },
    reload_column: function () {
        this.view.on_reload_column(this.row.res_id, this.col_offset);
    },
    /**
     *  Ouvre le pop-up de planification @todo fonction on_close
     */
    on_planning_creneau_secteur_action_clicked: function(ev){
        ev.preventDefault();
        //console.log(ev);
        var self = this;
        var action_id = "of_planning_view.action_view_of_planif_creneau_secteur_wizard"
        var additional_context = {
            "default_date_creneau": self.date,
            "default_employee_id": self.row.res_id,
            "default_secteur_id": self.secteur_id,
        };  // à voir quoi mettre
        //console.log("ADDITIONNAL CONTEXT",pyeval.eval('context', additional_context));

        return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
                //console.log("LE RESUUUULT",result);
                var options = {
                    'additional_context': pyeval.eval('context', additional_context),  // pour une raison inconnue le additional_context n'est pas pris en compte avant
                    'on_close': function () {self.reload_secteur();},
                };
                //return self.view.ViewManager.action_manager.ir_actions_act_window(result,options);
                return self.view.ViewManager.action_manager.do_action(result,options);
            }).then(function(){
                //$(".o_form_buttons_edit").eq(0).hide();  // cacher les boutons "Sauvergarder" et "Annuler"
            });
    },
    /**
     *  Ouvre le pop-up de sélection de secteur @todo fonction on_close
     */
    on_planning_creneau_action_clicked: function(ev){
        ev.preventDefault();
       //console.log(ev);
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
        };  // à voir quoi mettre
       //console.log("ADDITIONNAL CONTEXT",pyeval.eval('context', additional_context));

        return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
               //console.log("LE RESUUUULT",result);
                var options = {
                    'additional_context': pyeval.eval('context', additional_context),  // pour une raison inconnue le additional_context n'est pas pris en compte avant
                    'on_close': function () {self.reload_events();},
                    //'on_close': function () {self.reload_column();},
                };  // @todo: appel reload_column
                //return self.view.ViewManager.action_manager.ir_actions_act_window(result,options);
                return self.view.ViewManager.action_manager.do_action(result,options);
            }).then(function(){
                $(".o_form_buttons_edit").eq(0).hide();  // cacher les boutons "Sauvergarder" et "Annuler"
            });
    },
});


var PlanningRecord = Widget.extend({
    /**
     *  Widget de créneau d'intervention
     */
    init: function(row, view, record, options) {
        //console.log('MapRecord.init arguments: ',arguments);
        this.id = record.id;
        this._super(row);
        this.row = row;
        this.view = view;
        this.options = options;
        //this.color_bg = options.color_bg;
        //this.color_ft = options.color_ft;
        this.day_span = options.day_span;
        if (this.day_span > 1) this.$els = [];
        this.class ="of_planning_record of_planning_record_" + this.id;
        if (!isNullOrUndef(record.state_int)) this.class += " of_calendar_state_" + record["state_int"];
        if (this.day_span > 1) this.class += " of_planning_record_multiple";
        if (record.state_int == 3) this.class += " of_planning_info_annule_reporte";
        this.col_offset_start = options.col_offset_start;
        this.col_offset_stop = options.col_offset_stop;
        this.read_only_mode = options.read_only_mode || true; // current implementation solo readonly

        this.minimized = false;
        this.diplayable_content = {};

        this.date_start = record[this.view.date_start];
        this.date_stop = record[this.view.date_stop];
        this.type = "occupe";

        var self= this;
        this.record = record;
        var descript_dt = {type: "datetime"};
        var descript_ft = {type: "float_time"};
        this.heure_debut_str = formats.format_value(record.date,descript_dt).substring(11, 16);
        this.heure_fin_str = formats.format_value(record.date_deadline,descript_dt).substring(11, 16);
        this.heure_debut = hh_mm_to_float(this.heure_debut_str)
        this.heure_fin = hh_mm_to_float(this.heure_fin_str)
        //this.duree_str = formats.format_value(record.duree,descript_ft).replace(":", "h");
        var heures = Math.trunc(record.duree);
        var minutes = (record.duree - heures) * 60;
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
        this.address_city = record.address_city;
        this.address_zip = record.address_zip;
        this.secteur_name = record.secteur_id && record.secteur_id[1] || false;
        this.partner_name = record.partner_name;
        this.tache_name = record.tache_name;
        this.state_int = record.state_int;

        if (record[this.view.resource].length > 1) {  // several attendees
            this.attendee_other_ids = _.reject(record[this.view.resource], function (attendee_id) { return attendee_id == self.row.res_id})
           //console.log("this.attendee_other_ids",this.attendee_other_ids);
        }else{
            this.attendee_other_ids = []
        }
        this.on_global_click = _.debounce(this.on_global_click, 300, true);

        //this.init_content(record);
        //console.log('MapRecord this: ',this);
    },
    render: function(col_index) {
        var self = this;

        if (isNullOrUndef(col_index)) {
            col_index = Math.max(self.col_offset_start, 0);
        }
        //console.log("PLANNING_RECORD RENDER",col_index);
        self.color_bg = self.row.color_bg;
        self.color_ft = self.row.color_ft;
        if (isNullOrUndef(self.col_offset_stop)) {  // 1 day event
            return self.$el.html(qweb.render('PlanningView.record', {"record": self, "col_index": col_index})).promise()
                .then(function (){
                    var td_id = "of_planning_td_" + self.row.res_id + "_" + col_index;
                    //console.log("POSTRENDER ",self);
                    self.$el.appendTo("#" + td_id);
                    self.$el.on('click', self.proxy('on_global_click'));
                    self.$el.mouseover(self.on_planning_record_mouseover);
                    self.$el.mouseout(self.on_planning_record_mouseout);
                    var tooltip_opts = {
                        delay: { show: 501, hide: 0 },
                        //title: qweb.render('PlanningView.record.tooltip', {"record": self, "col_index": col_index}),
                    }
                    return qweb.render('PlanningView.record.tooltip', {"record": self, "col_index": self.col_offset_start})
                    //return self.$el.tooltip(tooltip_opts).promise()
                }).then(function (html) {
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
                //console.log("POSTRENDER ",self);
                self.$of_el[col_index].appendTo("#" + td_id);
                self.$of_el[col_index].on('click', self.proxy('on_global_click'));
                self.$of_el[col_index].mouseover(self.on_planning_record_mouseover);
                self.$of_el[col_index].mouseout(self.on_planning_record_mouseout);
                if (isNullOrUndef(self.tooltip_opts)) {
                    return qweb.render('PlanningView.record.tooltip', {"record": self, "col_index": self.col_offset_start});
                }
                return $.when();
            }).then(function (html) {
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
    on_global_click: function (ev) {
       //console.log("CLICLICLICLICLIC",ev);
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
    on_planning_record_mouseover: function(ev) {
        var record_class = "of_planning_record_" + this.id;
        var records = $("." + record_class)
        if (records.length > 1) {
            records.addClass("of_pulse");
        }
        var self = this;
        //console.log("records:",records);
    },
    on_planning_record_mouseout: function(ev) {
        var record_class = "of_planning_record_" + this.id;
        var records = $("." + record_class)
        if (records.length > 1) {
            records.removeClass("of_pulse");
        }
    },
    /* actions when user click on the block with a specific class
     *  open on normal view : oe_kanban_global_click
     *  open on form/edit view : oe_kanban_global_click_edit
     */
    on_card_clicked: function() {
        this.trigger_up('planning_record_open', {id: this.id});
    },
    on_planning_creneau_action_clicked: function (ev) {
       //console.log("HAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHA");
    },
    /**
     *
     */
    start: function () {
        //console.log("START PlanningRecord");;
        return this._super();
    },
});

PlanningView.Sidebar = Widget.extend({
    template: 'PlanningView.sidebar',

    start: function() {
        var self = this;
        this.caption = new SidebarCaption(this, this.getParent());
        this.reso_filter = new PlanningView.SidebarResoFilter(this, this.getParent());
        this.info_filter = new PlanningView.SidebarInfoFilter(this, this.getParent());
        return $.when(this._super(), this.reso_filter.appendTo(this.$el), this.info_filter.appendTo(this.$el), this.caption.appendTo(this.$el))
        .then(function() {
            self.caption.render();
        });
    }
});
PlanningView.SidebarResoFilter = Widget.extend({
    events: {
        'click .of_planning_contacts': 'on_click',
    },
    template: 'PlanningView.sidebar.reso_filters',

    init: function(parent, view) {
        this._super(parent);
        this.view = view;
    },
    render: function() {
        var self = this;
        self.$('.of_planning_contacts').html(qweb.render('PlanningView.sidebar.contacts', { filters: self.view.all_filters }));
    },
    on_click: function(e) {
        //console.log("CLICK");
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
        /*
            ir_values_model.call("set_default",
                ["of.intervention.settings",
                "planningview_filter_intervenant_" + e.target.value,
                e.target.checked, false]);
        */
        this.view.all_filters[e.target.value].is_checked = e.target.checked;
        if (e.target.checked) {
            this.view.filter_attendee_ids.push(parseInt(e.target.value));
            ir_values_model.call("set_default",
                ["of.intervention.settings",
                "planningview_filter_intervenant_ids",
                //[[6, 0, this.view.filter_attendee_ids]], false]);
                this.view.filter_attendee_ids, false]);
        }else{
            for (var i=0; i<this.view.filter_attendee_ids.length; i++) {
                if (this.view.filter_attendee_ids[i] == e.target.value) {
                    this.view.filter_attendee_ids.splice(i, 1); 
                }
            }
            ir_values_model.call("set_default",
                ["of.intervention.settings",
                "planningview_filter_intervenant_ids",
                this.view.filter_attendee_ids, false]);
        }
        var row_id = "of_planning_row_"+e.target.value;
        var la_row = this.view.rows[e.target.value];
        la_row.hidden = !e.target.checked;
        la_row.do_toggle(e.target.checked);
        //console.log("LA ROW",la_row);
        //this.trigger_up('reload_events');
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
        //this.on_click = _.debounce(this.on_click, 300, true);
        $.when(this.init_filters()).then(function(){self.render()});
    },
    init_filters: function() {
        var self = this;

        var check_tab_names = ["client","tache","zip","city","secteur","heure_debut","heure_fin","duree","annule_reporte"];
        var check_tab_vals = new Array(9);
        var check_tab_defs = new Array(9);
        var dfd = $.Deferred();
        var p = dfd.promise(self.info_filters);
        var defs = [], proms = [], les_args, le_def;
        var ir_values_model = new Model("ir.values");
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

        $.when.apply($, check_tab_defs)
        //$.when(check_tab_defs[0],check_tab_defs[1],check_tab_defs[2],check_tab_defs[3],check_tab_defs[4],check_tab_defs[5],check_tab_defs[6])
        .then(function () {
            //console.log("defs",defs);
            //console.log("check_tab_defs",check_tab_defs);
            //console.log("check_tab_vals",check_tab_vals);
            self.info_filters = {
                "client": {
                    "value": "client",
                    "input_id": "client_input",
                    "class": "of_planning_info_partner_name",
                    "label": "Client",
                    "is_checked": check_tab_vals[0],
                    "field_name_ir": "planningview_filter_client",
                },
                "tache": {
                    "value": "tache",
                    "input_id": "tache_input",
                    "class": "of_planning_info_tache_name",
                    "label": "Tache",
                    "is_checked": check_tab_vals[1],
                    "field_name_ir": "planningview_filter_tache",
                },
                "lieu": {
                    "value": "lieu",
                    "input_id": "lieu_input",
                    "class": "of_planning_info_lieu",
                    "label": "Lieu",
                    "is_checked": check_tab_vals[2] || check_tab_vals[3] || check_tab_vals[4],
                    "child_filters_visible": (local_storage.getItem('planningview_info_filters_visible_lieu') == 'true'),
                    "child_filters": {
                        "zip": {
                            "value": "lieu-zip",
                            "input_id": "lieu-zip_input",
                            "class": "of_planning_subinfo_zip",
                            "label": "Code postal",
                            "is_checked": check_tab_vals[2],
                            "field_name_ir": "planningview_filter_zip",
                        },
                        "city": {
                            "value": "lieu-city",
                            "input_id": "lieu-city_input",
                            "class": "of_planning_subinfo_city",
                            "label": "Ville",
                            "is_checked": check_tab_vals[3],
                            "field_name_ir": "planningview_filter_city",
                        },
                        "secteur": {
                            "value": "lieu-secteur",
                            "input_id": "lieu-secteur_input",
                            "class": "of_planning_subinfo_secteur",
                            "label": "Secteur",
                            "is_checked": check_tab_vals[4],
                            "field_name_ir": "planningview_filter_secteur",
                        },
                    },
                },
                "heures": {
                    "value": "heures",
                    "input_id": "heures_input",
                    "class": "of_planning_info_heures",
                    "label": "Heures / Durées",
                    "is_checked": check_tab_vals[7] || check_tab_vals[5] || check_tab_vals[6],
                    "child_filters_visible": (local_storage.getItem('planningview_info_filters_visible_heures') == 'true'),
                    "child_filters": {
                        "heure_debut": {
                            "value": "heures-heure_debut",
                            "input_id": "heures-heure_debut_input",
                            "class": "of_planning_subinfo_heure_debut",
                            "label": "Heure de début",
                            "is_checked": check_tab_vals[5],
                            "field_name_ir": "planningview_filter_heure_debut",
                        },
                        "heure_fin": {
                            "value": "heures-heure_fin",
                            "input_id": "heures-heure_fin_input",
                            "class": "of_planning_subinfo_heure_fin",
                            "label": "Heure de fin",
                            "is_checked": check_tab_vals[6],
                            "field_name_ir": "planningview_filter_heure_fin",
                        },
                        "duree": {
                            "value": "heures-duree",
                            "input_id": "heures-duree_input",
                            "class": "of_planning_subinfo_duree",
                            "label": "Durée",
                            "is_checked": check_tab_vals[7],
                            "field_name_ir": "planningview_filter_duree",
                        },
                    },
                },
                "annule_reporte": {
                    "value": "annule_reporte",
                    "input_id": "annule_reporte_input",
                    "class": "of_planning_info_annule_reporte",
                    "label": "Annulé / Reporté",
                    "is_checked": check_tab_vals[8],
                    "field_name_ir": "planningview_filter_annule_reporte",
                    "separated": true,
                },
            }
            self.view.info_filters = self.info_filters;
            dfd.resolve();
        });

        return p;
    },
    render: function() {
        var self = this;
        //console.log("info filters:",this.view.info_filters);

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
    apply_filters: function () {
        for (var f in this.info_filters) {
            //console.log("FFFFFF",f);
            var le_filter = this.info_filters[f], le_sub;
            var la_class = le_filter.class;
            if (le_filter.is_checked) {  // update event display
                $("."+la_class).removeClass("o_hidden");
            }else{
                //console.log(la_class,$("."+la_class));
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
    do_toggle_checked: function (checked, filter_value, rebounce=false) {
        var le_filter, le_parent, la_class, la_input_sel;
        var ir_values_model = new Model('ir.values');

        if ( filter_value instanceof Array) {
            le_parent = this.info_filters[filter_value[0]];
            le_filter = le_parent["child_filters"][filter_value[1]];
            le_filter.is_checked = checked;  // update data

            if (rebounce) {
                if (checked && !le_parent.is_checked) {  // check parent filter if at least one of the subfilters is checked
                    this.do_toggle_checked(true,filter_value[0],false);
                }else if (this.all_subfilters_unchecked(filter_value[0]) && le_parent.is_checked) {  // uncheck parent filter if none of the subfilters is checked
                    this.do_toggle_checked(false,filter_value[0],false);
                }
            }
        }else{
            le_filter = this.info_filters[filter_value];
            le_filter.is_checked = checked;  // update data

            if (rebounce && !isNullOrUndef(this.info_filters[filter_value].child_filters)) {  // filter has child filters: apply toggle to subfilters if rebounce=true
                var le_tab = [];
                for (var k in le_filter.child_filters) {
                    le_tab = [filter_value, k];
                    //console.log("LE_TAB",le_tab);
                    this.do_toggle_checked(checked, le_tab, false);
                }
            }

        }

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
        //console.log("le_filter['field_name_ir']",le_filter["field_name_ir"]);
        //console.log("le_filter",le_filter);

    },
    all_subfilters_unchecked: function (filter_value) {
        for (var k in this.info_filters[filter_value]["child_filters"]) {
            if (this.info_filters[filter_value]["child_filters"][k].is_checked) {
                return false;
            }
        }
        return true;
    },
    on_click: function(e) {
       //console.log("CLICK",e.target.tagName);
        //console.log("event target:",e.target);
        var la_value = e.target.value;
        var la_class;
        if (e.target.tagName == 'SPAN') {  // click sur span -> la checkboxe est a coté
            var la_input = e.target.previousElementSibling.firstElementChild;
            $("#"+la_input.id).click();
            return;
        }
        if (e.target.tagName == 'DIV') {  // click sur div
            if (e.target.className == "of_planning_ev_info" || e.target.className.indexOf("of_planning_ev_subinfo") != -1) {  // click sur div du filtre TODO className.indexOf
                $(e.target).find('input.' + e.target.className + '_input').click();
               //console.log("CASE AA");
                return;
            }else{  // click sur div du widget
               //console.log("CASE BB");
                return;
            }
        }
        if (e.target.tagName == 'I') {  // click sur i (montrer/cacher sous-filtres)
            //console.log(e);
            for (var i=0; i<e.target.classList.length; i++) {
                if (e.target.classList[i].indexOf("of_planning_ev_info_toggle") != -1) {
                    $("." + e.target.classList[i]).toggleClass("o_hidden");
                    break;
                }
            }
            la_value = e.target.id.split("_");
            if (la_value[1] == "show") {
                $(".of_planning_ev_subinfo_" + la_value[0]).removeClass("o_hidden");
                local_storage.setItem('planningview_info_filters_visible_' + la_value[0], true);
                //console.log("show",local_storage.getItem('planningview_info_filters_visible_'+la_value[0]));
            }else{
                $(".of_planning_ev_subinfo_" + la_value[0]).addClass("o_hidden");
                local_storage.setItem('planningview_info_filters_visible_' + la_value[0], false);
                //console.log("hide",local_storage.getItem('planningview_info_filters_visible_'+la_value[0]));
            }

            return;
        }
        var le_filter;
        if (la_value.indexOf("-") != -1) {
            la_value = la_value.split("-");
        }
        this.do_toggle_checked(e.target.checked, la_value, true);
    },
    on_click_show_filters: function(e) {
        //console.log("on_click_show_filters",e);
        this.$(".of_planning_info_filter_show").addClass("o_hidden");
        this.$(".of_planning_info_filter_hide").removeClass("o_hidden");
        this.do_toggle_filters(true);
    },
    on_click_hide_filters: function(e) {
        //console.log("on_click_hide_filters",e);
        this.$(".of_planning_info_filter_hide").addClass("o_hidden");
        this.$(".of_planning_info_filter_show").removeClass("o_hidden");
        this.do_toggle_filters(false);
    },
    do_toggle_filters: function(show) {
        if (show) {
            self.$('.of_planning_ev_infos').removeClass("o_hidden");
            this.info_filters_visible = true;
            local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        }else{
            self.$('.of_planning_ev_infos').addClass("o_hidden");
            this.info_filters_visible = false;
            local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        }
    },
});

var SidebarCaption = Widget.extend({
    /**
     *  called by Sidebar.start
     */
    init: function(parent, view) {
        this._super(parent);
        this.view = view;
        this.start();
    },

    start: function() {
        if (this.view.display_states) {
            this.$el.addClass("of_calendar_captions");
        };
        return $.when(this._super());
    },
    /**
     *  called by CalendarView._do_show_init
     */
    render: function () {
        var self = this;
        //if (this.view.display_states) {
            $.when(new Model(this.view.dataset.model).call('get_state_int_map'))
            .then(function (states){
                self.$el.html(qweb.render('CalendarView.sidebar.captions', { widget: self, captions: states }));
                self.do_show();
            });
        //}else{
        //    this.do_hide();
        //}
    },
});

core.view_registry.add('planning', PlanningView);

return PlanningView;
});
