odoo.define('of_calendar.calendar_view', function (require) {
"use strict";
/*---------------------------------------------------------
 * OpenFire calendar
 *---------------------------------------------------------*/

var core = require('web.core');
var CalendarView = require('web_calendar.CalendarView');
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');
var widgets = require('web_calendar.widgets');
var Model = require('web.DataModel');
var Widget = require('web.Widget');
var View = require('web.View');
var formats = require("web.formats");
var utils = require("web.utils");
var time = require('web.time');
var data = require("web.data");

var CompoundDomain = data.CompoundDomain;

var SidebarFilter = widgets.SidebarFilter;
var Sidebar = widgets.Sidebar;
var _t = core._t;
var QWeb = core.qweb;

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

function is_virtual_id(id) {
    return typeof id === "string" && id.indexOf('-') >= 0;
}

/**
 *  convertis une chaine de caractères de la forme #000000 en son tuple RGB équivalent
 */
function hexToRgb(hex, mod) {
    var parsed = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    var result = parsed ? {
        r: parseInt(parsed[1], 16),
        g: parseInt(parsed[2], 16),
        b: parseInt(parsed[3], 16)
    } : null;
    if (isNullOrUndef(hex)) {
        result = {
            r: 255,
            g: 255,
            b: 255
        }
    }else if (!isNullOrUndef(mod) && !isNullOrUndef(parsed)) {
        result["r"] = mod < 0 ? Math.max(0, result["r"] + mod) : Math.min(255, result["r"] + mod);
        result["g"] = mod < 0 ? Math.max(0, result["g"] + mod) : Math.min(255, result["g"] + mod);
        result["b"] = mod < 0 ? Math.max(0, result["b"] + mod) : Math.min(255, result["b"] + mod);
    }
    return result;
}

View.include({
    /**
     * When we go from one view to another, "o_content" element isn't always rebuilt.
     * We need to take out "of_scroll_hidden" if view is not calendar.
     * we want scrollbar hidden for mode day, else scrollbar appears after calculation of attendee columns width.
     * and ruins it in case of many attendees shown
     *
     * @returns {jQuery.Deferred or any}
     */
    start: function() {
        var $content = $(".o_content");
        if (this.template == "CalendarView") {
            $content.addClass("of_scroll_hidden");
        }else{
            $content.removeClass("of_scroll_hidden");
        }
        return $.when(this._super());
    },
});

CalendarView.include({
    custom_events: {
        reload_events: function () {
            this.$calendar.fullCalendar('refetchEvents');
        },
        'filters_rendered': 'on_filters_rendered',
    },

    init: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.view_manager = this.getParent();

        var attrs = this.fields_view.arch.attrs;
        this.filters_radio = !isNullOrUndef(attrs.filters_radio) && _.str.toBool(attrs.filters_radio);
        // true or 1 if we want to use custom colors
        this.custom_colors = !isNullOrUndef(attrs.custom_colors) && _.str.toBool(attrs.custom_colors);
        // true or 1 if we want to use multiple colors
        this.color_multiple = !isNullOrUndef(attrs.color_multiple) && _.str.toBool(attrs.color_multiple);
        this.jump_to = !isNullOrUndef(attrs.jump_to) && attrs.jump_to; // "first", "last" or "selected"
        this.dispo_field = attrs.dispo_field;
        this.force_color_field = attrs.force_color_field;
        this.selected_field = attrs.selected_field;

        this.color_ft_field = attrs.color_ft_field;
        this.color_bg_field = attrs.color_bg_field;
        if (this.fields[this.color_field].type == "many2many") {
            this.attendee_multiple = true;
        }
        if (this.custom_colors && !(attrs.color_ft_field && attrs.color_bg_field)) {
            throw new Error(_t("Calendar views with 'custom_colors' attribute set to true" +
                               "need to define both 'color_ft_field' and 'color_bg_field' attributes."));
        }
        this.attendee_model = attrs.attendee_model;
        // pour montrer tous les participants à droite au lieu de seulement ceux qui ont au moins un event
        this.show_all_attendees = !isNullOrUndef(attrs.show_all_attendees) && _.str.toBool(attrs.show_all_attendees);
        this.config_model = attrs.config_model || false;
        if (isNullOrUndef(this.avatar_title) && !isNullOrUndef(this.attendee_model)) {
            this.avatar_title = this.attendee_model;
        }
        if (this.custom_colors && !this.useContacts && isNullOrUndef(this.attendee_model)) {
            throw new Error(_t("Calendar views with 'custom_colors' attribute set to true" +
                               "need to define either 'use_contacts' or 'attendee_model' attribute. \n" +
                               "(use_contacts takes precedence)."));
        }
        if (!isNullOrUndef(attrs.draggable)) {
            this.draggable = _.str.toBool(attrs.draggable);
        }
        // integer to make state easily visible. see .less file
        this.display_states = attrs.display_states  && _.str.toBool(attrs.display_states);

        this.info_fields = [];
        for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
            if (isNullOrUndef(this.fields_view.arch.children[fld].attrs.invisible)) {
                // don't add field to description if invisible="1"
                this.info_fields.push(this.fields_view.arch.children[fld].attrs.name);
            }
        }
        this.icons = {}; // bottom icons
        for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
            var fieldIcon = this.fields_view.arch.children[fld].attrs.icon;
            if (!isNullOrUndef(fieldIcon)) { // is an icon field
                var fieldName = this.fields_view.arch.children[fld].attrs.name
                var iconPosition = this.fields_view.arch.children[fld].attrs.position
                if (isNullOrUndef(iconPosition)) { // default
                    iconPosition = "right";
                }
                this.icons[fieldName] = '<i class="fa fa-lg fa-' + fieldIcon + ' of_calendar_evt_bot of_calendar_evt_' +
                    iconPosition + '"/>';
            }
        }

        // if we don't have sidebar, (eg: Dashboard), we don't use the captions
        if (isNullOrUndef(this.options.sidebar)) {
            this.display_states = false;
        }

        this.res_ids_indexes = {}; // dictionnaire qui contient les indexes des filtres en fonction de leur id
        this.res_ids_attendee_columns = {};
        this.attendee_columns = [];
    },
    /**
     *  go to system parameters to see if we should allow drag and drop. Sets minTime and maxTime if needed
     */
    willStart: function() {
        var self = this;
        var ir_config_model = new Model('ir.config_parameter');
        var ir_values_model = new Model('ir.values');
        var dnd_dfd = ir_config_model.call('get_param',['Calendar_Drag_And_Drop']);
        var mintime_dfd = ir_values_model.call("get_default", ["of.intervention.settings", "calendar_min_time"]);
        var maxtime_dfd = ir_values_model.call("get_default", ["of.intervention.settings", "calendar_max_time"]);
        var company_ids_dfd = new Model('res.company').call('get_allowed_company_ids', []);

        // initialiser les couleurs des créneaux dispo et leur durée minimale
        var creneau_dispo_data_def = self.set_creneau_dispo_opt();

        return $.when(dnd_dfd, mintime_dfd, maxtime_dfd, company_ids_dfd, creneau_dispo_data_def, this._super())
        .then(function () {
            // privilégier l'attribut draggable de la vue XML si présent: exemple rdv_view.xml
            if (!isNullOrUndef(self.draggable)) {
                self.draggable = self.draggable;
            }else{
                self.draggable = _.str.toBool(arguments[0]);
            }
            var min_time = arguments[1];
            var max_time = arguments[2]
            if (min_time && min_time < 10) {  // minTime
                self.minTime = "0" + min_time + ":00:00"
            }else if (min_time) {
                self.minTime = min_time + ":00:00"
            }
            if (max_time && max_time < 10) {  // minTime
                self.maxTime = "0" + max_time + ":00:00"
            }else if (max_time) {
                self.maxTime = max_time + ":00:00"
            }
            self.company_ids = arguments[3]
            return $.when();
        });
    },
    /**
     * initialiser les filtres avant le start mais après tous les willStart hérités
     *
     * @returns {jQuery.Deferred or any}
     */
    start: function() {
        var self = this;
        var all_filters_dfd = $.Deferred();
        var all_filters_prom = all_filters_dfd.promise();
        if (self.attendee_model && self.show_all_attendees && !self.useContacts) {
            all_filters_prom = self._init_all_filters();
        }else{
            all_filters_dfd.resolve()
        }
        return $.when(all_filters_prom, this._super());
    },
    /**
     *  initialise les couleurs des créneaux dispos.
     *  Ainsi que la durée minimale pour qu'un créneau libre soit considéré comme disponible
     */
    set_creneau_dispo_opt: function () {
        var self = this;
        var ir_values_model = new Model("ir.values")
        var bg_def = ir_values_model.call("get_default", ["of.intervention.settings", "color_bg_creneaux_dispo"]);
        var ft_def = ir_values_model.call("get_default", ["of.intervention.settings", "color_ft_creneaux_dispo"]);
        var dureemin_def = ir_values_model.call("get_default", ["of.intervention.settings", "duree_min_creneaux_dispo"]);
        return $.when(bg_def, ft_def, dureemin_def)
        .then(function (bg, ft, duree) {
            self.creneau_dispo_opt = {
                'color_bg': bg,
                'color_ft': ft,
                'duree_min': duree,
            }
            return $.when();
        });
    },
    /**
     *  Hérité dans of_planning_view. Créé des évènements virtuels pour voir les créneaux dispo
     */
    set_res_horaires_data: function(res_ids=false, start=false, end=false, get_segments=false) {
        this.events_dispo = [];
        return $.when();
    },
    /**
     *  Hérité dans of_planning_view. Créé des évènements virtuels pour voir les jours fériés
     */
    set_events_feries: function(start) {
        this.events_feries = [];
        return $.when();
    },
    /**
     *  Quand l'attribut "show_all_attendees" est à 1, on charge tous les filtres au chargement de la vue
     *  plutôt que de les charger à chaque search
     */
    _init_all_filters: function () {
        var self = this;

        if (!self.config_model) {
            throw new Error("Attribut 'config_model' manquant dans la définition de la vue XML");
        }

        var dfd = $.Deferred();
        var p = dfd.promise();
        var Attendees = new Model(self.attendee_model);
        var attendee_domain = this.build_attendee_domain();

        Attendees.query(['id', self.color_ft_field, self.color_bg_field, 'name', 'sequence']) // retrieve colors from db
            .filter(attendee_domain)
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
                        value: a['id'],
                        input_id: a['id'] + "_input",
                        is_checked: true,
                        is_visible: true,
                        sequence: a['sequence'],
                        custom_colors: true,
                    }
                    self.all_filters[i] = filter_item;
                    self.res_ids_indexes[a['id']] = i;
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
    /**
     *  builds domain to filter attendees to be displayed in the right panel
     */
    build_attendee_domain: function() {
        var attendee_domain = ['|', ['company_id', '=', false], ['company_id', 'in', this.company_ids]];
        return new CompoundDomain(attendee_domain);
    },
    make_attendee_columns: function(){
        var self = this;
        var fil, attendee_col;
        self.attendee_columns = [];
        self.res_ids_attendee_columns = {}
        $.when(self.dfd_filters_rendered).then(function(){
            for (var i in self.all_filters) {
                fil = self.all_filters[i];
                // is_visible is not set on the odoo standard calendar
                if (fil.is_checked &&
                        (self.useContacts || fil.is_visible && isNullOrUndef(self.res_ids_attendee_columns[fil["value"]]))){
                    attendee_col = {
                        label: fil['label'],
                        color_bg: fil['color_bg'],
                        color_ft: fil['color_ft'],
                        value: fil['value'],
                        input_id: fil['value'] + "_input",
                        sequence: fil['sequence'],
                        is_attendee_col: true,
                        id: -100000 - fil['value'],  // be sure to have unique id
                        actual_id: fil['value'], // save actual id for fullcalendar library
                    }
                    attendee_col[self.color_field] = fil['value'];
                    self.attendee_columns.push(attendee_col);
                    self.res_ids_attendee_columns[fil["value"]] = self.attendee_columns.length - 1;
                }
            }
            self.dfd_attendee_col_made.resolve()
            return $.when()
        })
    },
    do_search: function (domain, context, _group_by) {
        var self = this;
        this.domain = domain;
        this.context = context;
        this.group_by = _group_by;

        this.shown.done(function () {
            self._do_search(domain, context, _group_by);
        });
    },
    /**
     * override copy of parent function. Sets up first event to be displayed. Handles radio filters
     */
    _do_search: function (domain, context, _group_by) {
        var self = this;
        // asynchronicity event colors. we need filteres to be rendered to know what color to put on events
        self.dfd_filters_rendered = $.Deferred();
        self.dfd_attendee_col_made = $.Deferred();
        if (!self.all_filters && self.useContacts) {
            self.all_filters = {};
        }else if (!self.all_filters) {
            self.all_filters = []
        }

        if (! _.isUndefined(this.event_source)) {
            this.$calendar.fullCalendar('removeEventSource', this.event_source);
        }
        this.event_source = {
            events: function(start, end, callback) {
                // catch invalid dates (start/end dates not parseable yet)
                // => ignore request
                if (isNaN(start) || isNaN(end)) {
                    return;
                }
                context['virtual_id'] = true;

                var current_event_source = self.event_source;
                    // pour sauter au dernier event il faut changer les bornes de recherche
                    // pour trouver l'event en question
                    // en attendant une meilleure solution, on passe par le contexte de recherche
                    if (context.force_date_start && !self.first_jump) {
                        start = moment(context.force_date_start)._d
                        end = moment(context.force_date_start).add(1, 'days')._d
                    }
                    var event_domain = self.get_range_domain(domain, start, end);
                    if (self.useContacts && (!self.all_filters[-1] || !self.all_filters[-1].is_checked)){
                        var attendee_ids = $.map(self.all_filters, function(o) { if (o.is_checked) { return o.value }});
                        if (!_.isEmpty(attendee_ids)) {
                            event_domain = new data.CompoundDomain(
                                event_domain,
                                [[self.attendee_people, 'in', attendee_ids]]
                            );
                        }
                    }

                // read_slice is launched uncoditionally, when quickly
                // changing the range in the calender view, all of
                // these RPC calls will race each other. Because of
                // this we keep track of the current range of the
                // calendar view.
                self.current_start = start;
                self.current_end = end;
                self.dataset.read_slice(_.keys(self.fields), {
                    offset: 0,
                    domain: event_domain,
                    context: context,
                }).done(function(events) {
                    ////////////////////////////////////////////////////////////////////////////////////////////////////
                    // this part is new. Sets up first event to be displayed
                    /*
                        Comportement: dans tous les cas on cherche notre premier event (même si jump_to est a selected)
                        comme ça si jump_to est a selected mais qu'il n'y a aucun event selected on sautera au premier
                    */
                    self.first_evt = events.length > 0 && events[0] || undefined;
                    if (!isNullOrUndef(self.jump_to) &&
                        !isNullOrUndef(self.first_evt) &&
                        !isNullOrUndef(self.dispo_field)) {
                        var tmp, strdate1, strdate2, strtime1, strtime2;
                        strdate1 = self.first_evt[self.date_start].substring(0,10);
                        strtime1 = self.first_evt[self.date_start].substring(11);
                        for (var i=1; i < events.length ; i++) {
                            tmp = events[i];
                            strdate2 = tmp[self.date_start].substring(0,10);
                            strtime2 = tmp[self.date_start].substring(11);
                            if (tmp[self.dispo_field]) {
                                if (!self.first_evt[self.dispo_field]) {  // in case first event isn't available
                                    self.first_evt = tmp;
                                    strdate1 = strdate2;
                                    strtime1 = strtime2;
                                } else if (strdate2 < strdate1) {
                                    self.first_evt = tmp;
                                    strdate1 = strdate2;
                                    strtime1 = strtime2;
                                } else if (strdate2 == strdate1 && strtime2 < strtime1) {
                                    self.first_evt = tmp;
                                    strdate1 = strdate2;
                                    strtime1 = strtime2;
                                }
                            }
                        }
                    }
                    if (self.jump_to == "last" && !isNullOrUndef(self.first_evt)) {
                        var last_index = events.length -1;
                        self.first_evt = events[last_index];
                    }
                    if (self.jump_to == "selected" && !isNullOrUndef(self.first_evt)) {
                        for (var i=1; i < events.length ; i++) {
                            if (events[i][self.selected_field]) {
                                self.first_evt = events[i];
                                break;
                            }
                        }
                    }
                    //////////////////////////////////////////////////////////////////////////////////////////////////*/
                    // undo the read_slice if it the range has changed since it launched
                    if (self.current_start.getTime() != start.getTime() || self.current_end.getTime() != end.getTime()){
                        self.dataset.ids = self.previous_ids;
                        return;
                    }
                    self.previous_ids = self.dataset.ids.slice();
                    if (self.dataset.index === null) {
                        if (events.length) {
                            self.dataset.index = 0;
                        }
                    } else if (self.dataset.index >= events.length) {
                        self.dataset.index = events.length ? 0 : null;
                    }

                    if (self.event_source !== current_event_source) {
                        console.log("Consecutive ``do_search`` called. Cancelling.");
                        return;
                    }

                    // If we use all peoples displayed in the current month as filter in sidebars
                    if (!self.useContacts && self.fields[self.color_field]) {
                        var filter_item;

                        self.now_filter_ids = [];

                        var color_field = self.fields[self.color_field];
                        ////////////////////////////////////////////////////////////////////////////////////////////////
                        // this part is modified /*

                        if (!self.show_all_attendees) {
                            var new_filter_added = false;
                            _.each(events, function (e) {
                                var key,val = null;
                                var is_visible, is_checked;

                                if (self.attendee_multiple) {
                                    _.each(e[self.color_field], function (a) {
                                        key = a;
                                        if (isNullOrUndef(self.res_ids_indexes[key])) {
                                            filter_item = {
                                                value: key,
                                                label: 'oupsy',
                                                color: self.get_color(key),
                                                avatar_model: (utils.toBoolElse(self.avatar_filter, true)
                                                               ? self.avatar_filter : false ),
                                                is_checked: true,
                                                is_visible: true
                                            };
                                            self.all_filters.push(filter_item);
                                            self.res_ids_indexes[key] = self.all_filters.length - 1;
                                            new_filter_added = true
                                        }
                                        is_visible = self.all_filters[self.res_ids_indexes[key]].is_visible;
                                        is_checked = self.all_filters[self.res_ids_indexes[key]].is_checked;
                                        if (! _.contains(self.now_filter_ids, key) && is_visible && is_checked) {
                                            self.now_filter_ids.push(key);
                                        }
                                    });
                                }else{
                                    if (color_field.type == "selection") {
                                        key = e[self.color_field];
                                        val = _.find(color_field.selection, function(name){ return name[0] === key;});
                                    } else {
                                        key = e[self.color_field][0];
                                        val = e[self.color_field];
                                    }
                                    if (isNullOrUndef(self.res_ids_indexes[key])) {
                                        filter_item = {
                                            value: key,
                                            label: val[1],
                                            color: self.get_color(key),
                                            avatar_model: (utils.toBoolElse(self.avatar_filter, true)
                                                           ? self.avatar_filter : false ),
                                            is_checked: true,
                                            is_visible: true
                                        };
                                        self.all_filters.push(filter_item);
                                        self.res_ids_indexes[key] = self.all_filters.length - 1;
                                        new_filter_added = true
                                    }
                                    is_visible = self.all_filters[self.res_ids_indexes[key]].is_visible;
                                    is_checked = self.all_filters[self.res_ids_indexes[key]].is_checked;
                                    if (! _.contains(self.now_filter_ids, key) && is_visible && is_checked) {
                                        self.now_filter_ids.push(key);
                                    }
                                }
                            });

                            // uncheck all but one filter if a new filter has been added
                            if (self.filters_radio && new_filter_added) {
                                var la_key = self.sidebar.filter.current_radio_key;
                                // initialiser self.sidebar.filter.current_radio_key si nécessaire
                                if (isNullOrUndef(la_key)) {
                                    if (!isNullOrUndef(self.first_evt)) {
                                        la_key = self.first_evt[self.color_field][0];
                                    }else{
                                        la_key = _.min(_.keys(self.res_ids_indexes));
                                    }
                                    self.sidebar.filter.current_radio_key = la_key;
                                }

                                for(var key in self.res_ids_indexes){
                                    if (key == la_key) {
                                        self.all_filters[self.res_ids_indexes[key]].is_checked = true;
                                    }else{
                                        self.all_filters[self.res_ids_indexes[key]].is_checked = false;
                                    }
                                };
                            }
                        }else{
                            for (var ii=0; ii<self.all_filters.length; ii++) {
                                if (self.all_filters[ii].is_checked && self.all_filters[ii].is_visible) {
                                    self.now_filter_ids.push(self.all_filters[ii].value);
                                }
                            }
                        }

                        if (self.sidebar) {
                            // ne conserver que les events qui ont au moins un attendee coché dans les filtres
                            self.sidebar.filter.render();
                            self.event_ids_attendees = {};
                            var events_temp = [], e;
                            for (var ie=0; ie<events.length; ie++) {
                                e = events[ie];
                                e.view = self;
                                self.event_ids_attendees[e["id"]] = [];
                                if (self.attendee_multiple) {
                                    var keys = e[self.color_field];
                                    var key;
                                    for (var i in keys) {
                                        key = keys[i];
                                        if (_.contains(self.now_filter_ids, key) &&
                                            self.all_filters[self.res_ids_indexes[key]].is_checked) {
                                            // at least one of the attendees of this events is checked in the filters
                                            events_temp.push(e);
                                            // quand on montre les créneaux dispo,
                                            // on duplique les events pour conserver l'alignement des colonnes
                                            // on duplique également les events en mode jour pour les placer dans toutes
                                            // les colonnes d'attendee concernées
                                            // TODO : ne pas dupliquer les events all_day en mode semaine et mois?
                                            if (!(self.show_creneau_dispo || self.is_mode_day())) {
                                                break;
                                            }
                                        }
                                    }
                                }else{
                                    var key = color_field.type == "selection"
                                        ? e[self.color_field] : e[self.color_field][0];
                                    if (_.contains(self.now_filter_ids, key) &&
                                        self.all_filters[self.res_ids_indexes[key]].is_checked) {
                                        events_temp.push(e);
                                    }
                                }
                            }
                            events = events_temp;
                        }else{
                            self.dfd_filters_rendered.resolve()
                        }
                    }else{
                        self.event_ids_attendees = {};
                        var events_temp = []
                        for (var ie=0; ie<events.length; ie++) {
                            events[ie].view = self;
                            self.event_ids_attendees[events[ie]["id"]] = [];
                            if (self.attendee_multiple) {
                                var keys = events[ie][self.color_field];
                                var key, added = false;
                                for (var i in keys) {
                                    key = keys[i];
                                    if (_.contains(self.now_filter_ids, key) &&
                                        self.all_filters[self.res_ids_indexes[key]].is_checked) {
                                        // at least one of the attendees of this events is checked in the filters
                                        events_temp.push(events[ie]);
                                        added = true;
                                        // quand on montre les créneaux dispo,
                                        // on duplique les events pour conserver l'alignement des colonnes
                                        // on duplique également les events en mode jour pour les placer dans toutes
                                        // les colonnes d'attendee concernées
                                        if (!(self.show_creneau_dispo || self.is_mode_day())) {
                                            break;
                                        }
                                    }
                                }
                                // si aucun participant n'a son filtre coché
                                // mais que le filtre "tout le monde" est coché, on ajoute l'event
                                if (!added && self.all_filters[-1] && self.all_filters[-1].is_checked) {
                                    events_temp.push(events[ie]);
                                }
                            }else{
                                events_temp.push(events[ie])
                            }
                        }
                        events = events_temp;
                        self.dfd_filters_rendered.resolve()
                    }
                    // calculer les créneaux dispo
                    self.dfd_res_horaires_calc = $.Deferred();
                    self.set_res_horaires_data(self.now_filter_ids, start, end).then(function(){
                        self.dfd_res_horaires_calc.resolve()
                    });
                    // caluler les jours fériés
                    self.dfd_events_feries = $.Deferred();
                    self.set_events_feries(start, end).then(function(){
                        self.dfd_events_feries.resolve()
                    });
                    // initialisation all_attendees, utilisé dans event_data_transform
                    var color_field = self.fields[self.color_field];
                    if (color_field.type == "many2many" || color_field.type == "selection") {
                        var all_attendees = $.map(events, function (e) { return e[self.color_field]; });
                    }else{
                        var all_attendees = $.map(events, function (e) { return e[self.color_field][0]; });
                    }
                    all_attendees = _.chain(all_attendees).flatten().uniq().value();

                    self.all_attendees = {};
                    if (self.is_mode_day()) {
                        self.make_attendee_columns();
                    }else{
                        self.dfd_attendee_col_made.resolve();
                    }
                    if (self.avatar_title !== null) {
                        new Model(self.avatar_title)
                            .query(["name"])
                            .filter([["id", "in", all_attendees]])
                            .all()
                            .then(function(result) {
                                _.each(result, function(item) {
                                    self.all_attendees[item.id] = item.name;
                                });
                            })
                            .done(function() {
                                // dfd_attendee_col_made résolu implique dfd_filters_rendered résolu
                                return $.when(
                                    self.dfd_attendee_col_made, self.dfd_res_horaires_calc, self.dfd_events_feries)
                            .then(function() {
                                return self.perform_necessary_name_gets(events)
                            })
                            .then(function(){
                                // ajouter les créneaux dispo
                                for (var i=0; i<self.events_dispo.length; i++) {
                                    self.events_dispo[i].view = self;
                                    events.push(self.events_dispo[i]);
                                }
                                // ajouter les jours fériés (fonctionnalité implémentée dans of_planning_view)
                                for (var j=0; j<self.events_feries.length; j++) {
                                    self.events_feries[j].view = self;
                                    events.push(self.events_feries[j]);
                                }

                                if (self.is_mode_day()) {
                                    // ajouter les events d'attendees seulement en mode jour
                                    for (var k=0; k<self.attendee_columns.length; k++) {
                                        self.attendee_columns[k].view = self;
                                        events.push(self.attendee_columns[k]);
                                    }
                                }
                                self.events = events;
                                return events;
                            })
                            .then(callback);
                        });
                    }else{
                        _.each(all_attendees,function(item){
                                self.all_attendees[item] = '';
                        });
                        return $.when(self.dfd_filters_rendered, self.dfd_res_horaires_calc)
                        .then(function() {
                            return self.perform_necessary_name_gets(events)
                        })
                        .then(function(){
                            for (var i=0; i<self.events_dispo.length; i++) {
                                self.events_dispo[i].view = self;
                                events.push(self.events_dispo[i]);
                            }
                            self.events = events;
                            return events;
                        })
                        .then(callback);
                    }
                    //////////////////////////////////////////////////////////////////////////////////////////////////*/
                });
            },
            eventDataTransform: function (event) {
                return self.event_data_transform(event);
            },
        };
        this.$calendar.fullCalendar('addEventSource', this.event_source);
    },
    /**
     *  Override of parent function
     *  render states caption if display_states in attributes
     */
    _do_show_init: function () {
        this._super.apply(this,arguments);
        if (this.color_multiple) {
            this.sidebar.color_filter.render();
        }
        if (this.model == "of.planning.intervention") {
            this.sidebar.creneau_dispo_filter.render();
        }
        if (this.display_states) {
            this.sidebar.caption.render();
        }
    },
    /**
     *  update drag n drop, minTime, maxTime
     */
    get_fc_init_options: function () {
        var fc = this._super();
        var self = this;
        // make sure attendee columns are loaded when starting on mode week and going on mode day
        fc.lazyFetching = false;
        fc.editable = this.draggable;
        fc.minTime = this.minTime;
        fc.maxTime = this.maxTime;
        fc.slotEventOverlap = false;
        // don't display a line for all_day events if there is no all_day field declared in the view
        if (!self.all_day) {
            fc.allDaySlot = false;
        }
        // Replace made to remove seconds. Must be done twice, once for date_start and once for date_end
        fc.timeFormat = fc.timeFormat = fc.timeFormat.replace(':ss', '').replace(':ss', '');
        // callback
        fc.eventAfterAllRender = function(view) {
            self.on_event_after_all_render();
        };
        fc.select = function (start_date, end_date, all_day, attendees, _js_event, _view) {
            if (self.options.action && self.options.action.context && self.options.action.context.inhiber_create) {
                Dialog.alert(self.$el, self.options.action.context.inhiber_message);  // inhiber création
                self.$calendar.fullCalendar('unselect');
            }else{
                var data_template = self.get_event_data({
                    start: start_date,
                    end: end_date,
                    allDay: all_day,
                });
                // prefill attendees in the event to be created
                if (self.attendee_people && attendees && attendees.length) {
                    if (self.fields[self.attendee_people].type == "many2many") {
                        data_template[self.attendee_people] = attendees;
                    }else{
                        data_template[self.attendee_people] = attendees[0];
                    }
                }
                self.open_quick_create(data_template);
            }
        }
        fc.eventDrop = function (event, _day_delta, _minute_delta, _all_day, _revertFunc) {
            // inhiber drag and drop pour les les créneaux dispo
            if (event["id"] < 0) {
                Dialog.alert(
                    self.$el,
                    "Le drag and drop (glisser/déposer) n'est pas possible ni pour les créneaux dispos, " +
                    "ni pour les jours fériés."
                );
                _revertFunc();
                return
            }
            // inhiber le drag and drop pour les évènement régulier
            if (typeof(event["id"]) == "string") {
                Dialog.alert(
                    self.$el,
                    "Le drag and drop (glisser/déposer) n'est pas possible pour les évènements réguliers."
                );
                _revertFunc();
                return
            }
            // copie du code odoo car héritage impossible
            var data = self.get_event_data(event);
            self.proxy('update_record')(event._id, data); // we don't revert the event, but update it.

            // en cas de drag n drop on ne repasse pas par do_search,
            // il faut donc réinitialiser self.event_ids_attendees[event["id"]]
            if (isNullOrUndef(self.event_ids_attendees)) {
                self.event_ids_attendees = {};
            }

            self.event_ids_attendees[event["id"]] = [];
        }
        fc.eventResize = function (event, _day_delta, _minute_delta, _revertFunc) {
            if (event["id"] < 0) {
                Dialog.alert(
                    self.$el,
                    "Il n'est pas possible de redimensionner un créneau dispo"
                );
                _revertFunc();
                return
            }
            // copie du code odoo car héritage impossible
            var data = self.get_event_data(event);
            self.proxy('update_record')(event._id, data);
            // en cas de redimensionnage on ne repasse pas par do_search,
            // il faut donc réinitialiser self.event_ids_attendees[event["id"]]
            if (isNullOrUndef(self.event_ids_attendees)) {
                self.event_ids_attendees = {};
            }
            self.event_ids_attendees[event["id"]] = [];
        }
        fc.eventClick = function (event) { self.open_event(event); };
        fc.eventRender = function (event, element, view) {
            var etitle = event.title;
            // Avoid to display the title with an 'undifined' value.
            // Because if the event has no employee this is a virtual event and attendee_avatars is undifined here.
            if (event.attendee_avatars != undefined) {
                etitle += event.attendee_avatars;
            }
            element.find('.fc-event-title').html(etitle);
        }
        return fc;
    },
    init_calendar: function() {
        var self = this;
        return $.when(this._super()).then(function(){self.view_inited = true;})
    },
    get_view_event_by_id: function(id) {
        var event;
        for (var i=0; i<this.events.length; i++) {
            event = this.events[i];
            if (event.id == id) {
                return event;
            }
        }
        return false;
    },
    /**
     *  Jumps to first event rather than current day
     */
    on_event_after_all_render: function() {
        // Cette fonction est appelée 2 fois quand une view est chargée dans un onglet qui n'est pas affiché en premier.
        // Dans ce cas le do_search est appelé mais n'initialise aucun events. Et donc add_tooltip ne fait rien.
        var self = this;
        var event;
        // only jump once, else we can't navigate through the calendar
        if (!isNullOrUndef(self.first_evt) && !self.first_jump && !!self.jump_to) {
            self.first_jump = true;
            var date_tmp = moment(self.first_evt[self.date_start])._d;
            if (!isNaN(date_tmp.getTime())) {
                self.$calendar.fullCalendar('gotoDate', date_tmp);
            }
        }
        // pas d'info-bulle pour le calendrier standard odoo à l'heure actuelle
        if (!self.useContacts) {
            for (var i=0; i<self.events.length; i++) {
                event = self.events[i];
                self.add_tooltip(event);
            }
        }
    },
    add_tooltip: function(event) {
        var $ev, self=this;
        $ev = $(".of_event_" + event.id);
        $ev.tooltip({
                        delay: { show: 501, hide: 0 },
                        title: QWeb.render('CalendarView.record.tooltip', {"record": event}),
                    })
    },
    /**
     *  Handler pour le signal 'filters rendered' envoyé par SidebarFilter
     */
    on_filters_rendered: function() {
        this.dfd_filters_rendered.resolve();
    },
    /**
     *  called by CalendarView.get_all_filters_ordered if custom_colors set to true
     *  sets custom colors for all_filter.
     */
    _set_all_custom_colors: function() {
        var self = this;
        if (self.show_all_attendees) {
            return $.when();
        }
        if (self.useContacts) {  // dans le calendrier standard self.all_filters est un dictionnaire et non une liste
            for (var k in self.all_filters) {
                self.res_ids_indexes[k] = k;
            }
        }
        var ids = _.keys(self.res_ids_indexes)

        var dfd = $.Deferred();
        var p = dfd.promise({target: kays});
        var kays = [];
        var model_name;
        if (self.useContacts) {
            model_name = "res.partner";
        }else{
            model_name = self.attendee_model;
        }
        var Attendees = new Model(model_name);
        Attendees.query(['id', 'name', self.color_ft_field, self.color_bg_field]) // retrieve colors from db
            .filter([['id','in',ids]]) // id
            .all()
            .then(function (attendees){
                for (var i=0; i<attendees.length; i++) {
                    var a = attendees[i];
                    var key = a.id;
                    kays.push(key);
                    self.all_filters[self.res_ids_indexes[key]]['color_bg'] = a[self.color_bg_field];
                    self.all_filters[self.res_ids_indexes[key]]['color_ft'] = a[self.color_ft_field];
                    self.all_filters[self.res_ids_indexes[key]]['custom_colors'] = true;
                    self.all_filters[self.res_ids_indexes[key]]['label'] = a['name'];
                    self.all_filters[self.res_ids_indexes[key]]['useContacts'] = self.useContacts;
                };
                if (self.useContacts) {
                    self.all_filters[-1]['color_bg'] = '#C0FFE8';
                    self.all_filters[-1]['color_ft'] = '#0D0D0D';
                    self.all_filters[-1]['custom_colors'] = true;
                    self.all_filters[-1]['label'] = 'Tout le monde';
                    self.all_filters[-1]['useContacts'] = true;
                };
                dfd.resolve();
            });

        return $.when(p);
    },
    /**
     *  Override of parent function. Adds custom colors to filters.
     *  called by SidebarFilter.render()
     */
    get_all_filters_ordered: function() {
        var self = this
        var filters = self._super();
        var dfd = $.Deferred();
        var p = dfd.promise({target: filters});
        if (!self.custom_colors) {
            dfd.resolve();
        }else{
            $.when(self._set_all_custom_colors()).then(function() {
                dfd.resolve();
            });
        }
        return p;
    },
    /**
     *  Returns the first value in indexes that is in self.all_custom_colors
     *  Returns -1 if no match
     */
    get_custom_color_index: function(indexes) {
        var self = this;
        var i = 0, res = -1;
        while (i < indexes.length && res == -1) {
            if (indexes[i] in self.all_filters) {
                res = indexes[i];
            };
            i++;
        }
        return res;
    },
    open_event: function(event) {
        var self = this;
        var id = event._id;
        var title = event.title;
        if (! this.open_popup_action) {
            var index = this.dataset.get_id_index(event._id);
            this.dataset.index = index;
            if (this.create_right && id <= -1) {
                var data_template = self.get_event_data({
                    start: event.start,
                    end: event.end,
                    allDay: event.allDay,
                });
                for (var k in event.defaults) {
                    data_template[k] = event.defaults[k];
                }
                self.open_quick_create(data_template);
            }else if (this.write_right) {
                this.do_switch_view('form', { mode: "edit" });
            }else{
                this.do_switch_view('form', { mode: "view" });
            }
        }else{
            var res_id = parseInt(id).toString() === id ? parseInt(id) : id;
            new form_common.FormViewDialog(this, {
                res_model: this.model,
                res_id: res_id,
                context: this.dataset.get_context(),
                title: title,
                view_id: +this.open_popup_action,
                readonly: true,
                buttons: [
                    {text: _t("Edit"), classes: 'btn-primary', close: true, click: function() {
                        self.dataset.index = self.dataset.get_id_index(id);
                        self.do_switch_view('form', { mode: "edit" });
                    }},

                    {text: _t("Delete"), close: true, click: function() {
                        self.remove_event(res_id);
                    }},

                    {text: _t("Close"), close: true}
                ]
            }).open();
        }
        return false;
    },
    /**
     * Transform fullcalendar event object to OpenERP Data object. inherited to add attendee data
     */
    get_event_data: function(event) {
        var data = this._super.apply(this, arguments);
        data['attendees'] = event['attendees'];
        return data;
    },
    /**
     * Surcharge de la fonction parente car elle n'est pas héritable.
     * Updates record identified by ``id`` with values in object ``data``
     */
    update_record: function(id, data) {
        var self = this;
        var event_id;
        delete(data.name); // Cannot modify actual name yet
        var index = this.dataset.get_id_index(id);
        if (index !== null) {
            var attendee_field = this.attendee_people;
            if (attendee_field) {
                if (self.fields[attendee_field] && self.fields[attendee_field].type == "many2many") {
                    data[attendee_field] = [[6, 0, data["attendees"]]];
                } else if (self.fields[attendee_field] && self.fields[attendee_field].type == "many2one") {
                    // M2O : [id, name]
                    data[attendee_field] = data["attendees"][0];
                }
            }
            delete(data.attendees);
            event_id = this.dataset.ids[index];
            this.dataset.write(event_id, data, {context: {from_ui: true}}).always(function() {
                if (self.show_creneau_dispo) {
                    self.$calendar.fullCalendar('refetchEvents');
                }else{
                    if (is_virtual_id(event_id)) {
                        // this is a virtual ID and so this will create a new event
                        // with an unknown id for us.
                        self.$calendar.fullCalendar('refetchEvents');
                    } else {
                        // classical event that we can refresh
                        self.refresh_event(event_id);
                        var view_event = self.get_view_event_by_id(id);
                        self.add_tooltip(view_event);
                    }
                }
            });
        }
        return false;
    },
    /**
     * Override copy of parent function. Add custom colors, multiple colors, forced colors, suffix
     * Transform OpenERP event object to fullcalendar event object
     */
    event_data_transform: function(evt) {
        var self = this;
        var date_start;
        var date_stop;
        var date_delay = evt[this.date_delay] || 1.0,
            all_day = this.all_day ? evt[this.all_day] : false,
            res_computed_text = '',
            the_title = '',
            attendees = [];

        date_start = time.auto_str_to_date(evt[this.date_start]);
        date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop]) : null;

        if (evt["is_attendee_col"]) {
            // pas besoin de calculs pour le titre des events de participants
            the_title = evt.label;
        } else if (this.info_fields) {
            var temp_ret = {};
            res_computed_text = this.how_display_event;
            _.each(this.info_fields, function (fieldname) {
                var value = evt[fieldname];
                if (_.contains(["many2one"], self.fields[fieldname].type)) {
                    if (value === false) {
                        temp_ret[fieldname] = null;
                    }
                    else if (value instanceof Array) {
                        temp_ret[fieldname] = value[1]; // no name_get to make
                    }
                    else if (_.contains(["date", "datetime"], self.fields[fieldname].type)) {
                        temp_ret[fieldname] = formats.format_value(value, self.fields[fieldname]);
                    }
                    else if (!evt["ferie"]) {
                        throw new Error("Incomplete data received from dataset for record " + evt.id);
                    }
                }
                else if (_.contains(["one2many","many2many"], self.fields[fieldname].type)) {
                    if (value === false) {
                        temp_ret[fieldname] = null;
                    }
                    else if (value instanceof Array)  {
                        temp_ret[fieldname] = value; // if x2many, keep all id !
                    }
                    else if (!evt["ferie"]) {
                        throw new Error("Incomplete data received from dataset for record " + evt.id);
                    }
                }
                else {
                    temp_ret[fieldname] = value;
                }
                // suffix
                if (!isNullOrUndef(self.fields[fieldname].__attrs["suffix"])) {
                    temp_ret[fieldname] = temp_ret[fieldname] + self.fields[fieldname].__attrs["suffix"];
                }
                res_computed_text = res_computed_text.replace("["+fieldname+"]",temp_ret[fieldname]);
            });

            if (res_computed_text.length) {
                the_title = res_computed_text;
            }
            else {
                var res_text= [];
                _.each(temp_ret, function(val,key) {
                    if( typeof(val) === 'boolean' && val === false ) { }
                    else { res_text.push(val); }
                });
                the_title = res_text.join(', ');
            }
            the_title = _.escape(the_title);

            var color_captions = false;
            if (self.color_multiple) {
                var color_filter = self.sidebar.color_filter
                var current_filter = color_filter.color_filter_data[color_filter.current_radio_key]
                color_captions = current_filter.captions
            }

            var the_title_avatar = '';

            if (! _.isUndefined(this.attendee_people) && this.fields[this.attendee_people].type == "many2many") {
                var MAX_ATTENDEES = 10;
                var attendee_showed = 0;
                var attendee_other = '';
                var found = false;
                var icon_offset_px = 2;  // 2 + 15 * nb_icon_places

                _.each(evt[this.attendee_people],
                    function (the_attendee_people) {
                        attendees.push(the_attendee_people);
                        attendee_showed += 1;
                        if (attendee_showed<= MAX_ATTENDEES) {
                            if (self.avatar_model !== null) {
                                the_title_avatar += '<img title="' + _.escape(self.all_attendees[the_attendee_people]) +
                                                    '" class="o_attendee_head"' + 'src="/web/image/' +
                                                    self.avatar_model + '/' + the_attendee_people +
                                                    '/image_small"></img>';
                                var now_id;

                                now_id = the_attendee_people;
                                if (!isNullOrUndef(self.all_filters[self.res_ids_indexes[now_id]]) &&
                                        self.all_filters[self.res_ids_indexes[now_id]].is_checked && !found &&
                                        !isNullOrUndef(self.event_ids_attendees[evt["id"]]) &&
                                        !_.contains(self.event_ids_attendees[evt["id"]], now_id)) {
                                    // quand on montre les créneaux dispo,
                                    // on duplique les events à plusieurs attendees pour avoir un bel alignement
                                    // il faut donc leur donner chacun une couleur différente
                                    evt["color_filter_id"] = now_id;
                                    self.event_ids_attendees[evt["id"]].push(now_id);
                                    found = true;
                                }
                            }else{
                                if (!self.attendee_multiple && !self.custom_colors && (!self.colorIsAttendee ||
                                    the_attendee_people != evt[self.color_field])) {
                                    var tempColor = (self.all_filters[self.res_ids_indexes[the_attendee_people]] !== undefined)
                                                ? self.all_filters[self.res_ids_indexes[the_attendee_people]].color
                                                : (self.all_filters[-1] ? self.all_filters[-1].color : 1);
                                    the_title_avatar += '<i class="fa fa-user o_attendee_head o_underline_color_' +
                                                        tempColor+'" title="' +
                                                        _.escape(self.all_attendees[the_attendee_people]) + '" ></i>';
                                }else if (self.attendee_multiple && isNullOrUndef(evt["virtuel"])) {
                                    var tempColorFT, tempColorBG;
                                    var now_id;

                                    now_id = the_attendee_people;
                                    // if this attendee is not present in self.all_filters, it means they belong to a
                                    // a company that is not in current user's authorized companies
                                    // in this case, don't do anything
                                    if (!isNullOrUndef(self.all_filters[self.res_ids_indexes[now_id]])) {
                                        tempColorFT = self.all_filters[self.res_ids_indexes[now_id]].color_ft;
                                        tempColorBG = self.all_filters[self.res_ids_indexes[now_id]].color_bg;
                                        // this will be the main color of the event
                                        if (self.all_filters[self.res_ids_indexes[now_id]].is_checked && !found &&
                                            !isNullOrUndef(self.event_ids_attendees[evt["id"]]) &&
                                            !_.contains(self.event_ids_attendees[evt["id"]], now_id)) {
                                            // quand on montre les créneaux dispo,
                                            // on duplique les events à plusieurs attendees pour avoir un bel alignement
                                            // il faut donc leur donner chacun une couleur différente
                                            evt["color_filter_id"] = now_id;
                                            self.event_ids_attendees[evt["id"]].push(now_id);
                                            found = true;
                                            if (!self.colorIsAttendee || color_captions) {
                                                the_title_avatar +=
                                                    '<i class="of_calendar_evt_top of_calendar_attendee_box" title="' +
                                                    _.escape(self.all_attendees[the_attendee_people]) + '"' +
                                                    'style="background: ' + tempColorBG +
                                                    '; border: 1px solid #0D0D0D; position: absolute; right: ' +
                                                    icon_offset_px + 'px;" ></i>';
                                                    icon_offset_px += 15;
                                            }
                                        }else{
                                            the_title_avatar +=
                                                '<i class="of_calendar_evt_top of_calendar_attendee_box" title="' +
                                                _.escape(self.all_attendees[the_attendee_people]) + '"' +
                                                'style="background: ' + tempColorBG +
                                                '; border: 1px solid #0D0D0D; position: absolute; right: ' +
                                                icon_offset_px + 'px;" ></i>';
                                            icon_offset_px += 15;
                                        }
                                    }
                                }else if (evt["virtuel"] && !evt["ferie"]){
                                    var tempColorFT, tempColorBG;
                                    var now_id;

                                    now_id = the_attendee_people;
                                    tempColorFT = self.all_filters[self.res_ids_indexes[now_id]].color_ft;
                                    tempColorBG = self.all_filters[self.res_ids_indexes[now_id]].color_bg;
                                    the_title_avatar +=
                                        '<i class="of_calendar_evt_top of_calendar_attendee_box" title="' +
                                        _.escape(self.all_attendees[the_attendee_people]) + '"' +
                                        'style="background: ' + tempColorBG +
                                        '; border: 1px solid #0D0D0D; position: absolute; right: ' + icon_offset_px +
                                        'px;" ></i>';
                                }
                            }
                        }else{
                            attendee_other += _.escape(self.all_attendees[the_attendee_people]) +", ";
                        }
                    }
                );
                if (evt["color_filter_id"] && attendees.length > 1) {
                    // placer le color_filter_id en premier dans la liste pour le tri par fullcalendar
                    var attendees_temp = [evt["color_filter_id"]];
                    for (var ai=0; ai<attendees.length; ai++) {
                        if (attendees[ai] != evt["color_filter_id"]) {
                            attendees_temp.push(attendees[ai]);
                        }
                    }
                    attendees = attendees_temp;
                }
                if (attendee_other.length>2) {
                    the_title_avatar += '<span class="o_attendee_head" title="' + attendee_other.slice(0, -2) +
                                        '">+</span>';
                }
            } else if (! _.isUndefined(this.attendee_people) && this.fields[this.attendee_people].type == "many2one") {
                // M2O fields are of form [<id>, <name>]
                attendees.push(evt[this.attendee_people][0]);
            }

        }

        if (!date_stop && date_delay) {
            var m_start = moment(date_start).add(date_delay,'hours');
            date_stop = m_start.toDate();
        }
        var r = {
            'start': moment(date_start).toString(),
            'end': moment(date_stop).toString(),
            'title': the_title,
            'allDay': (this.fields[this.date_start].type == 'date' || (this.all_day && evt[this.all_day]) || false),
            'id': evt.id,
            'attendees':attendees,
            'is_attendee_col': evt.is_attendee_col,
            'is_holiday': evt.ferie,  // fonctionnement ajouté dans fullcalendar pour l'affichage en mode jour
        };
        if (evt.employee_id != false) {
            r['attendee_avatars'] = the_title_avatar;
        }
        for (var key in self["icons"]) {
            if (evt[key]) {
                r.title = r.title + self["icons"][key];
            }
        }
        if (self.custom_colors) {
            // couleur forcée
            if (evt[self.force_color_field]) {
                r.backgroundColor = evt[self.force_color_field];
                r.textColor = "#0C0C0C";
            // evt de titre de colonne de participant
            }else if (evt["is_attendee_col"]) {
                r.backgroundColor = evt["color_bg"];
                r.textColor = evt["color_ft"];
                r.actual_id = evt["actual_id"];
            // evt dispo
            }else if (evt[self.dispo_field]) {  // evt is phantom
                r.backgroundColor = self.creneau_dispo_opt['color_bg'];
                r.textColor = self.creneau_dispo_opt['color_ft'];
            // utilisation de calendar.contact
            }else if (self.useContacts) {
                var index = self.get_custom_color_index(r.attendees);
                r.backgroundColor = self.all_filters[self.res_ids_indexes[index]]['color_bg'];
                r.textColor = self.all_filters[self.res_ids_indexes[index]]['color_ft'];
            }else if (self.attendee_multiple) {  // multiple attendees
                if (!isNullOrUndef(evt["color_filter_id"])) {
                    if (evt["ferie"]) {
                        r.textColor = evt[self.color_ft_field];
                        r.backgroundColor = self.jours_feries_opt.color_jours_feries;
                    }else if (evt["virtuel"]) {
                        var rgb_bg = hexToRgb(self.creneau_dispo_opt['color_bg']);
                        var rgb_ft = hexToRgb(self.creneau_dispo_opt['color_ft']);
                        r.backgroundColor = "rgba(" + rgb_bg.r + "," + rgb_bg.g + "," + rgb_bg.b + ",0.2);";
                        r.textColor = "rgba(" + rgb_ft.r + "," + rgb_ft.g + "," + rgb_ft.b + ",0.5)";
                    }else{
                        r.backgroundColor = self.all_filters[ self.res_ids_indexes[evt["color_filter_id"]] ]['color_bg'];
                        r.textColor = self.all_filters[ self.res_ids_indexes[evt["color_filter_id"]] ]['color_ft'];
                    }
                }else{
                    console.log("oups! something went wrong with multiple attendees colors for evt",evt);
                }
            }else if (evt[self.color_ft_field] && evt[self.color_bg_field]) {
                r.textColor = evt[self.color_ft_field];
                r.backgroundColor = evt[self.color_bg_field];
            }else{
                throw new Error(_t("Missing fields in calendar view definition: '" +
                                   self.color_ft_field + "' and/or '" + self.color_bg_field + "'."));
            }
            r.className = ["of_custom_color"];
            if (self.attendee_multiple) {
                // ajout de class pour le pulse quand filtre survolé par la souris
                for (var i=0; i<evt[self.color_field].length; i++) {
                    r.className.push("of_calendar_attendee_" + evt[self.color_field][i]);
                }
            }
            // ajout du pulse si l'evt est sélectionné
            if (evt[self.selected_field]) {
                r.className.push("of_pulse");
            }
            // ajout de classe en fonction de l'état
            if (self.display_states) {
                r.className.push("of_calendar_state_" + evt["state_int"]);
                r.borderColor = "rgba( 0, 0, 0, 0.0)"; // border to represent state
            }else{
                r.borderColor = "rgba( 0, 0, 0, 0.7)";
            }
            // ajout d'une classe pour lier l'élement HTML à l'objet javascript
            r.className.push("of_event_" + evt.id);

            // events virtuels -> faire passer des infos de valeur par défaut de champs au moment du click
            if (evt["virtuel"]) {
                r.defaults = evt["defaults"];
            }
        }else{ // debug of odoo code
            var color_key = evt[this.color_field];
            // make sure color_key is an integer before testing self.all_filters[color_key]
            if (typeof color_key === "object") {
                color_key = color_key[0];
            }
            if (!self.useContacts || self.all_filters[self.res_ids_indexes[color_key]] !== undefined) {
                if (color_key) {
                    r.className = 'o_calendar_color_'+ this.get_color(color_key);
                }
            } else { // if form all, get color -1
                r.className = 'o_calendar_color_'+ (self.all_filters[-1] ? self.all_filters[-1].color : 1);
            }
        };
        // color_captions  == false -> la couleur de l'evt est celle des attendees et donc déjà initialisée
        if (color_captions && !evt["virtuel"]) {
            var caption_key = evt[current_filter.field]
            // make sure caption_key is an integer before testing captions[caption_key]
            if (typeof caption_key === "object") {
                caption_key = caption_key[0];
            }
            if (isNullOrUndef(color_captions[caption_key])) {
                if (!isNullOrUndef(color_captions[-1])) {
                    r.textColor = color_captions[-1]["color_ft"];
                    r.backgroundColor = color_captions[-1]["color_bg"];
                }else{
                    r.textColor = "#0D0D0D";
                    r.backgroundColor = "#F0F0F0";
                }
            }else{
                r.textColor = color_captions[caption_key]["color_ft"];
                r.backgroundColor = color_captions[caption_key]["color_bg"];
            }
        }
        if (evt["virtuel"]) {
            r.className.push("of_calendar_virtuel");
        }
        // formatage des heures pour affichage dans tooltip
        var descript_ft = {type: "float_time"};
        if (evt["virtuel"]) {
            r["heure_debut_str"] = formats.format_value(evt.heure_debut,descript_ft);
            r["heure_fin_str"] = formats.format_value(evt.heure_fin,descript_ft);
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
        }
        // colonnes vue jour
        if (self.useContacts && isNullOrUndef(self.res_ids_attendee_columns[r["attendees"][0]])) {
            r.attendee_column = self.res_ids_attendee_columns["-1"];
        }else{
            r.attendee_column = self.res_ids_attendee_columns[r["attendees"][0]];
        }
        evt.r = r;
        return r;
    },
    /**
     *  Works when get_actual_mode doesn't, My guess is that it's faster and beats asynchronicity
     */
    is_mode_day: function () {
        var $fc_view = this.$calendar.find('.fc-view');
        var res = ($fc_view.length > 0 && $fc_view.hasClass('fc-view-agendaDay'));
        return res;
    },
    /**
     *  Returns "day", "week" or "month instead of "agendaDay", "agendaWeek" or "month" (yeah...)
     */
    get_actual_mode: function () {
        var fullcal_mode = this.$calendar.fullCalendar('getView').name;
        if (fullcal_mode == "agendaWeek") {
            return "week"
        }else if ("agendaDay") {
            return "day"
        }
        return "month"
    },
});

Sidebar.include({
    /**
     *  called by Sidebar.start
     */
    init: function(parent, view) {
        this._super(parent);
        this.view = this.getParent();
    },
    /**
     *  Override of parent function. Adds captions.
     */
    start: function() {
        this.caption = new SidebarCaption(this, this.view);
        if (this.view.color_multiple) {
            this.color_filter = new SidebarColorFilter(this, this.getParent());
        }
        if (this.view.model == "of.planning.intervention") {
            this.creneau_dispo_filter = new SidebarCreneauDispoFilter(this, this.getParent());
        }
        return $.when(this._super(), this.caption.appendTo(this.$el))
    },
});

SidebarFilter.include({
    events: {
        'click .o_calendar_contact': 'on_click',
        'click .o_remove_contact': 'on_remove_filter',
        'mouseover .of_calendar_filter': 'on_mouseover',
        'mouseout .of_calendar_filter': 'on_mouseout',
    },
    init: function(parent, view) {
        this._super(parent,view);
        this.filters_radio = view.filters_radio;
    },
    /**
     *  Override of parent function. handles asynchronicity.
     */
    render: function() {
        var self = this;
        if (this.view.show_all_attendees) {
            var filters_radio = self.filters_radio || false;
            return $.when(self.$('.o_calendar_contacts').html(QWeb.render('CalendarView.sidebar.contacts',
                                                              { filters: this.view.all_filters, filters_radio: filters_radio })))
                .then(function(){return self.trigger_up('filters_rendered')});
        }else{
            var fil = self.view.get_all_filters_ordered()
            //async
            $.when(fil).then(function(){ // fil is a promise
                var filters = fil.target;
                var filters_radio = self.filters_radio || false;
                return $.when(self.$('.o_calendar_contacts').html(QWeb.render('CalendarView.sidebar.contacts',
                                                                  { filters: filters, filters_radio: filters_radio })))
                    .then(function(){return self.trigger_up('filters_rendered')});
            });
        }
    },
    _remove_filter: function (value) {
        delete this.view.res_ids_indexes[value];
        return this._super(value);
    },
    /**
     *  Override of parent function. handles radio filters.
     */
    on_click: function(e) {
        if (e.target.tagName !== 'INPUT') {
            $(e.currentTarget).find('input').click();
            return;
        }
        var all_filters = this.view.all_filters;
        this.view.now_filter_ids = [];
        if (this.filters_radio) {
            for(var i in all_filters){
                if (all_filters[i].value == e.target.value) {
                    all_filters[i].is_checked = e.target.checked;
                    this.current_radio_key = all_filters[i].value;
                    this.view.now_filter_ids.push(this.current_radio_key);
                }else{
                    all_filters[i].is_checked = false;
                }
            };
        }else{
            all_filters[this.view.res_ids_indexes[e.target.value]].is_checked = e.target.checked;
            for(var i in all_filters) {
                if (all_filters[i].is_checked) {
                    this.view.now_filter_ids.push(all_filters[i].value);
                }
            }
        }
        if (this.view.config_model) {
            var ir_values_model = new Model("ir.values");
            ir_values_model.call("set_default",
                    [this.view.config_model,
                    "of_filter_attendee_ids",
                    this.view.now_filter_ids, false]);
        }
        this.trigger_up('reload_events');
    },
    on_mouseout: function (ev) {
        if (!this.filters_radio) {
            var class_a_pulse = ev.target.id;
            if (class_a_pulse) {
                $("." + class_a_pulse).removeClass("of_pulse");
            }
        }
    },
    on_mouseover: function (ev) {
        if (!this.filters_radio) {
            var class_a_pulse = ev.target.id;
            if (class_a_pulse) {
                $("." + class_a_pulse).addClass("of_pulse");
            }
        }
    },
});
/**
 *  Widget pour permettre un choix dans la colorisation des events
 */
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
        this.ready_to_render = $.Deferred();
        this.willStart();
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
            // Le Qweb a besoin de 2 variables même si les 2 pointent sur self.color_filter_data
            return self.$el.html(QWeb.render('CalendarView.sidebar.color_filter',
                                             {widget: self,
                                              filters: self.color_filter_data,
                                              filter_captions: self.color_filter_data})).promise();
        }).then(function() {
            return self.$el.insertAfter($(".o_calendar_filter"))
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
                if (this.view.config_model) {
                    // Conserver le choix de colorisation des évènements
                    ir_values_model.call("set_default", [this.view.config_model,
                                                         "of_event_color_filter",
                                                         key, false]);
                }
            }else{
                this.color_filter_data[key].is_checked = false;
            }
        };
        this.render();
        this.trigger_up('reload_events');
    },
});


var SidebarCreneauDispoFilter = Widget.extend({
    events: {
        'click .of_creneau_dispo_filter': 'on_click',
    },
    /**
     *  called by Sidebar.start
     */
    init: function(parent, view) {
        this._super(parent,view);
        this.view = view;
        this.ready_to_render = $.Deferred();
        this.willStart();
    },
    willStart: function () {
        var self = this;
        var ir_values_model = new Model("ir.values");
        this.dfd_filter_is_checked = ir_values_model.call("get_default", [this.view.config_model,
                                                                          "of_show_creneau_dispo",
                                                                          false]);
        return $.when(this.dfd_filter_is_checked, this._super()).then(function (filter_is_checked) {
            self.filter_is_checked = filter_is_checked || false;
            self.view.show_creneau_dispo = self.filter_is_checked;
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
            return self.$el.html(QWeb.render('CalendarView.sidebar.creneau_dispo_filter',
                                             {widget: self,
                                              filter_is_checked: self.filter_is_checked})).promise();
        }).then(function() {
            return self.$el.insertAfter($(".o_calendar_filter"))
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
        this.filter_is_checked = e.target.checked;
        this.view.show_creneau_dispo = this.filter_is_checked;
        if (this.view.config_model) {
            // Conserver le choix de colorisation des évènements
            ir_values_model.call("set_default", [this.view.config_model,
                                                 "of_show_creneau_dispo",
                                                 this.filter_is_checked, false]);
        }
        this.render();
        this.trigger_up('reload_events');
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
            this.$el.addClass("of_sidebar_element");
        };
        return $.when(this._super());
    },
    /**
     *  called by CalendarView._do_show_init
     */
    render: function () {
        var self = this;
        if (this.view.display_states) {
            $.when(new Model(this.view.dataset.model).call('get_state_int_map'))
            .then(function (states){
                self.$el.html(QWeb.render('CalendarView.sidebar.captions', { widget: self, captions: states }));
                self.do_show();
            });
        }else{
            this.do_hide();
        }
    },
});

return {
    SidebarCaption: SidebarCaption
};

});
