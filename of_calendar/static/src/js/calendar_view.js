odoo.define('of_calendar.calendar_view', function (require) {
"use strict";
/*---------------------------------------------------------
 * OpenFire calendar
 *---------------------------------------------------------*/

var core = require('web.core');
var data_manager = require('web.data_manager');
var pyeval = require('web.pyeval');
var CalendarView = require('web_calendar.CalendarView');
var Dialog = require('web.Dialog');
var widgets = require('web_calendar.widgets');
var Model = require('web.DataModel');
var Widget = require('web.Widget');
var formats = require("web.formats");
var utils = require("web.utils");
var time = require('web.time');
var data = require("web.data");

var SidebarFilter = widgets.SidebarFilter;
var Sidebar = widgets.Sidebar;
var _t = core._t;
var QWeb = core.qweb;

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

CalendarView.include({
    custom_events: {
        reload_events: function () {
            this.$calendar.fullCalendar('refetchEvents');
        },
        'filters_rendered': 'on_filters_rendered',
        'res_horaires_calc': 'on_res_horaires_calc',
    },

    init: function () {
        var self = this;
        this._super.apply(this, arguments);

        var attrs = this.fields_view.arch.attrs;
        this.filters_radio = !isNullOrUndef(attrs.filters_radio) && _.str.toBool(attrs.filters_radio); // true or 1 if we want filters to be of type radio
        this.custom_colors = !isNullOrUndef(attrs.custom_colors) && _.str.toBool(attrs.custom_colors); // true or 1 if we want to use custom colors
        //this.show_first_evt = !isNullOrUndef(attrs.show_first_evt) && _.str.toBool(attrs.show_first_evt); // true or 1 if we want to jump to the first event
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
            throw new Error(_t("Calendar views with 'custom_colors' attribute set to true need to define both 'color_ft_field' and 'color_bg_field' attributes."));
        }
        this.attendee_model = attrs.attendee_model;
        if (isNullOrUndef(this.avatar_title) && !isNullOrUndef(this.attendee_model)) {
            this.avatar_title = this.attendee_model;
        }
        if (this.custom_colors && !this.useContacts && isNullOrUndef(this.attendee_model)) {
            throw new Error(_t("Calendar views with 'custom_colors' attribute set to true need to define either 'use_contacts' or 'attendee_model' attribute. \n\
                (use_contacts takes precedence)."));
        }
        this.draggable = !isNullOrUndef(attrs.draggable)  && _.str.toBool(attrs.draggable); // make drag n drop defaults to false

        this.display_states = attrs.display_states  && _.str.toBool(attrs.display_states); // integer to make state easily visible. see .less file

        this.info_fields = [];
        for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
            if (isNullOrUndef(this.fields_view.arch.children[fld].attrs.invisible)) {
                this.info_fields.push(this.fields_view.arch.children[fld].attrs.name); // don't add field to description if invisible="1"
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
                this.icons[fieldName] = '<i class="fa fa-lg fa-' + fieldIcon + ' of_calendar_evt_bot of_calendar_evt_' + iconPosition + '"/>'
            }
        }

        // if we have not sidebar, (eg: Dashboard), we don't use the captions
        if (isNullOrUndef(this.options.sidebar)) {
            this.display_states = false;
        }

        this.on_event_after_all_render = _.debounce(this.on_event_after_all_render, 300, true);
    },
    /**
     *  go to system parameters to see if we should allow drag and drop. Sets minTime and maxTime if needed
     */
    willStart: function() {
        var self = this;
        //var dfd = $.Deferred();
        //var dfd2 = $.Deferred();
        //var dfd3 = $.Deferred();
        var ir_config_model = new Model('ir.config_parameter');
        var ir_values_model = new Model('ir.values');
        var dnd_dfd = ir_config_model.call('get_param',['Calendar_Drag_And_Drop']);
        var mintime_dfd = ir_values_model.call("get_default", ["of.intervention.settings", "calendar_min_time"]);
        var maxtime_dfd = ir_values_model.call("get_default", ["of.intervention.settings", "calendar_max_time"]);

        return $.when(dnd_dfd, mintime_dfd, maxtime_dfd, this._super())
        .then(function () {
            self.draggable = _.str.toBool(arguments[0]) || self.draggable; // if false in system parameters but true in view definition, make it true
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
            return $.when();
        });
    },
    set_res_horaires_data: function(res_ids=false, start=false, end=false, get_segments=false) {
        var self = this;
        var dfd = $.Deferred();
        var p = dfd.promise()
        res_ids = res_ids || self.view_res_ids;
        start = start || self.range_start;
        end = moment(start).endOf(this.mode || "week")._d;
        console.log(this.mode);
        console.log("start/range_start",start,self.range_start);
        console.log("end/range_stop",end,self.range_stop);

        var Planning = new Model(self.model);
        Planning.call('get_emp_horaires_info', [res_ids, start, end, get_segments])
        .then(function (result) {
            if (isNullOrUndef(self.res_horaires_info)) {
                self.res_horaires_info = result;
            }else{
                for (var i=0; i<res_ids.length; i++) {
                    self.res_horaires_info[res_ids[i]] = result[res_ids[i]];
                }
            }

            dfd.resolve();
        });
        return $.when(p).then(function() {
            //console.log("créneaux dispo",self.res_horaires_info);
            self.events_dispo = [];
            var cmpt_events = 0;
            var attendee_data, creneaux_dispo_jour, creneau_dispo;
            for (var k in self.res_horaires_info) {
                //console.log("k",k);
                attendee_data = self.res_horaires_info[k];
                for (var i=0; i<attendee_data.creneaux_dispo.length; i++) {
                    //console.log("i",i);
                    creneaux_dispo_jour = attendee_data.creneaux_dispo[i];
                    for (var j=0; j<creneaux_dispo_jour.length; j++) {
                        creneau_dispo = creneaux_dispo_jour[j];
                        creneau_dispo["calendar_name"] = "Dispo";
                        creneau_dispo["color_filter_id"] = k;
                        //creneau_dispo["date_prompt"] = "Dispo";
                        //creneau_dispo["date_deadline_prompt"] = "Dispo";
                        creneau_dispo["employee_ids"] = [k];
                        creneau_dispo["id"] = -1;
                        creneau_dispo["of_color_bg"] = "#FFFFFF";
                        creneau_dispo["of_color_ft"] = "#000000";
                        creneau_dispo["state"] = "Dispo";
                        creneau_dispo["state_int"] = 0;
                        creneau_dispo["disponible"] = true;
                        creneau_dispo["index"] = cmpt_events;
                        cmpt_events++;
                        self.events_dispo.push(creneau_dispo)
                        //console.log("j",j);
                    }
                }
            }
            return $.when();
        });
    },
    /**
     * override copy of parent function. Sets up first event to be displayed. Handles radio filters
     */
    _do_search: function (domain, context, _group_by) {
        var self = this;
        self.dfd_filters_rendered = $.Deferred(); // asynchronicity event colors. we need filteres to be rendered to know what color to put on events
        self.dfd_res_horaires_calc = $.Deferred();
        if (! self.all_filters) {
            self.all_filters = {};
        }

        if (! _.isUndefined(this.event_source)) {
            this.$calendar.fullCalendar('removeEventSource', this.event_source);
        }
        this.event_source = {
            events: function(start, end, callback) {
                self.dfd_res_horaires_calc = $.Deferred();
                // catch invalid dates (start/end dates not parseable yet)
                // => ignore request
                if (isNaN(start) || isNaN(end)) {
                    return;
                }

                var current_event_source = self.event_source;
                    // pour sauter au dernier event il faut changer les bornes de recherche pour trouver l'event en question
                    // en attendant une meilleure solution, on passe par le contexte de recherche
                    if (context.force_date_start && !self.first_jump) {
                        start = moment(context.force_date_start)._d
                        end = moment(context.force_date_start).add(1, 'days')._d
                    }
                    var event_domain = self.get_range_domain(domain, start, end);
                    if (self.useContacts && (!self.all_filters[-1] || !self.all_filters[-1].is_checked)){// || self.attendee_multiple) {
                        var attendee_ids = $.map(self.all_filters, function(o) { if (o.is_checked) { return o.value; }});
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
                    //////////////////////////////////////////////////////////////////////////////////// this part is new. Sets up first event to be displayed
                    /*
                        Comportement: dans tous les cas on cherche notre premier event (même si jump_to est a selected)
                        comme ça si jump_to est a selected mais qu'il n'y a aucun event selected on sautera au premier
                    */
                    //console.log("EVENTS",events);
                    self.first_evt = events.length > 0 && events[0] || undefined;
                    if (!isNullOrUndef(self.jump_to) && !isNullOrUndef(self.first_evt) && !isNullOrUndef(self.dispo_field)) {
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
                    ///////////////////////////////////////////////////////////////////////////////////*/
                    // undo the read_slice if it the range has changed since it launched
                    if (self.current_start.getTime() != start.getTime() || self.current_end.getTime() != end.getTime()) {
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

                    if (!self.useContacts && self.fields[self.color_field]) {  // If we use all peoples displayed in the current month as filter in sidebars
                        var filter_item;

                        self.now_filter_ids = [];

                        var color_field = self.fields[self.color_field];
                        ///////////////////////////////////////////////////////////////////////////// this part is modified
                        var all_filters_temp = _.clone(self.all_filters);
                        var new_filter_added = false;
                        _.each(events, function (e) {
                            var key,val = null;

                            if (self.attendee_multiple) {
                                _.each(e[self.color_field], function (a) {
                                    key = a;
                                    if (!all_filters_temp[key]) {
                                        filter_item = {
                                            value: key,
                                            label: 'oupsy',
                                            color: self.get_color(key),
                                            avatar_model: (utils.toBoolElse(self.avatar_filter, true) ? self.avatar_filter : false ),
                                            is_checked: true
                                        };
                                        all_filters_temp[key] = filter_item;
                                        new_filter_added = true
                                    }
                                    if (! _.contains(self.now_filter_ids, key)) {
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
                                if (!all_filters_temp[key]) {
                                    filter_item = {
                                        value: key,
                                        label: val[1],
                                        color: self.get_color(key),
                                        avatar_model: (utils.toBoolElse(self.avatar_filter, true) ? self.avatar_filter : false ),
                                        is_checked: true
                                    };
                                    all_filters_temp[key] = filter_item;
                                    new_filter_added = true
                                }
                                if (! _.contains(self.now_filter_ids, key)) {
                                    self.now_filter_ids.push(key);
                                }
                            }
                        });
                        if (self.filters_radio && new_filter_added) {  // uncheck all but one filter if a new filter has been added
                            var la_key;
                            if (!isNullOrUndef(self.first_evt)) {
                                la_key = self.first_evt[self.color_field][0];
                            }else{
                                la_key = _.min(_.keys(all_filters_temp));
                            }
                            self.current_radio_key = la_key;
                            for(var key in all_filters_temp){
                                if (key == la_key) {
                                    all_filters_temp[key].is_checked = true;
                                }else{
                                    all_filters_temp[key].is_checked = false;
                                }
                            };
                        }
                        self.all_filters = all_filters_temp;

                        //var dfd_filters_rendered = $.Deferred();
                        if (self.sidebar) {
                            self.sidebar.filter.render();
                            //$.when(self.sidebar.filter.render()).then(function(){return dfd_filters_rendered.resolve()});
                            //setTimeout(function(){return dfd_filters_rendered.resolve()}, 100);

                            events = $.map(events, function (e) {
                                if (self.attendee_multiple) {
                                    var keys = e[self.color_field];
                                    var key;
                                    for (var i in keys) {
                                        key = keys[i];
                                        if (_.contains(self.now_filter_ids, key) &&  self.all_filters[key].is_checked) {
                                            // at least one of the attendees of this events is checked in the filters
                                            return e;
                                        }
                                    }
                                }else{
                                    var key = color_field.type == "selection" ? e[self.color_field] : e[self.color_field][0];
                                    if (_.contains(self.now_filter_ids, key) &&  self.all_filters[key].is_checked) {
                                        return e;
                                    }
                                }
                                return null;
                            });
                        }else{
                            self.dfd_filters_rendered.resolve()
                            console.log("OUPSY NO SIDEBAR")
                        }
                    }
                    self.set_res_horaires_data(self.now_filter_ids, start, end).then(function(){
                        //console.log("events",events);
                        //console.log("self.events_dispo",self.events_dispo);
                        //events += self.events_dispo;
                        self.dfd_res_horaires_calc.resolve()
                    });
                    

                    var all_attendees = $.map(events, function (e) { return e[self.attendee_people]; });
                    all_attendees = _.chain(all_attendees).flatten().uniq().value();

                    self.all_attendees = {};
                    if (self.avatar_title !== null) {
                        new Model(self.avatar_title).query(["name"]).filter([["id", "in", all_attendees]]).all().then(function(result) {
                            _.each(result, function(item) {
                                self.all_attendees[item.id] = item.name;
                            });
                        }).done(function() {
                            return $.when(self.dfd_filters_rendered, self.dfd_res_horaires_calc)
                            .then(function() {
                                return self.perform_necessary_name_gets(events)
                            })
                            .then(function(){
                                for (var i=0; i<self.events_dispo.length; i++) {
                                    events.push(self.events_dispo[i]);
                                }
                                //console.log(events);
                                return events;
                            })
                            .then(callback);
                            //return self.perform_necessary_name_gets(events).then(callback);
                        });
                    }
                    else {
                        _.each(all_attendees,function(item){
                                self.all_attendees[item] = '';
                        });
                        //return self.perform_necessary_name_gets(events).then(callback)
                        return $.when(self.dfd_filters_rendered, self.dfd_res_horaires_calc)
                            .then(function() {
                                return self.perform_necessary_name_gets(events)
                            })
                            .then(function(){
                                for (var i=0; i<self.events_dispo.length; i++) {
                                    events.push(self.events_dispo[i]);
                                }
                                //console.log(events);
                                return events;
                            })
                            .then(callback);//, 100);  // ici
                    }
                    //////////////////////////////////////////////////////////////////////////////////
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
        fc.editable = this.draggable;
        fc.minTime = this.minTime;
        fc.maxTime = this.maxTime;
        fc.timeFormat = fc.timeFormat.replace(':ss', '');
        // callback
        fc.eventAfterAllRender = function(view) {
            self.on_event_after_all_render();
        };
        fc.select = function (start_date, end_date, all_day, _js_event, _view) {
            if (self.options.action.context.inhiber_create) {
                Dialog.alert(self.$el, self.options.action.context.inhiber_message);  // inhiber création
                self.$calendar.fullCalendar('unselect');
            }else{
                var data_template = self.get_event_data({
                    start: start_date,
                    end: end_date,
                    allDay: all_day,
                });
                self.open_quick_create(data_template);
            }
        };
        fc.eventClick = function (event, ev) { console.log("click event",event,ev)
                                            self.on_click(event, ev); };
        return fc;
    },
    /**
     *  Jumps to first event rather than current day
     */
    on_event_after_all_render: function() {
        var self = this;
        // only jump once, else we can't navigate through the calendar
        if (!!self.jump_to && !isNullOrUndef(self.first_evt) && !self.first_jump) {
            self.first_jump = true;
            var date_tmp = moment(self.first_evt[self.date_start])._d;
            if (!isNaN(date_tmp.getTime())) {
                self.$calendar.fullCalendar('gotoDate', date_tmp);
            }
        }
        var el_style = "float: right; top: 0px; height: 50%; width: 100%; background-color: rgba(0, 0, 0, 0.4)";
        var el_attrs = {
            style: el_style,
            class: "of_calendar_search",
        };
        var el = self.make("div", el_attrs);
        $(".of_calendar_dispo").find('.fc-event-bg').append(el);
        console.log("after render calendar search", $(".of_calendar_search").length);
        $(".of_calendar_dispo").mouseover(self.on_dispo_mouseover);
    },
    /**
     *  event est le créneau, ev est l'évènement javascript
     */
    on_click: function (event, ev) {
        var self = this;
        if ($(ev.target).hasClass("of_calendar_search")) {
            console.log("CLICK DISPO",ev);
            var creneau_dispo = self.events_dispo[event.index_dispo];
            var action_id = "of_planning_view.action_view_of_planif_wizard"
            var additional_context = {
                "default_heure_debut_creneau": creneau_dispo.heure_debut,
                "default_heure_debut_rdv": creneau_dispo.heure_debut,
                "default_heure_fin_creneau": creneau_dispo.heure_fin,
                "default_lieu_prec_id": creneau_dispo.lieu_debut.id || false,
                "default_lieu_suiv_id": creneau_dispo.lieu_fin.id || false,
                "default_date_creneau": creneau_dispo.date,
                "default_duree_creneau": creneau_dispo.duree,
                "default_employee_id": creneau_dispo.color_filter_id,
                "default_secteur_id": creneau_dispo.secteur_id,
                "default_creneaux_reels": creneau_dispo.creneaux_reels.length > 0 ? creneau_dispo.creneaux_reels : false,
                "default_warning_horaires": creneau_dispo.warning_horaires,
            };

            return data_manager.load_action(action_id, pyeval.eval('context', additional_context)).then(function(result) {
                    var options = {
                        'additional_context': pyeval.eval('context', additional_context),  // pour une raison inconnue le additional_context n'est pas pris en compte avant
                        'on_close': function () {self.reload_events();},
                    };
                    return self.ViewManager.action_manager.do_action(result,options);
                }).then(function(){
                    $(".o_form_buttons_edit").eq(0).hide();  // cacher les boutons "Sauvergarder" et "Annuler"
                });
        }else{
            self.open_event(event);
        }
    },
    on_click_dispo: function(ev) {
        console.log("CLICK DISPO",ev);
    },
    on_dispo_mouseover: function(ev) {
        /*console.log("HAHA",ev, _.contains(ev.target.classList, "of_calendar_dispo_mouseover"));
        var self = this;
        var el_style = "float: right; top: 0px; height: 50%; width: 100%; background-color: rgba(0, 0, 0, 0.4)";
        var el_attrs = {
            style: el_style,
            class: "of_calendar_dispo_mouseover",
        };
        var el = self.make("div", el_attrs);
        if (!$(ev.target).hasClass("of_calendar_dispo_mouseover") && !$(ev.target).siblings(".of_calendar_dispo_mouseover").length) {
            ev.target.append(el);
        }else{
            console.log("ah...");
        }*/
        
    },
    on_filters_rendered: function() {
        this.dfd_filters_rendered.resolve();
    },
    on_res_horaires_calc: function() {
        this.dfd_res_horaires_calc.resolve();
    },
    /**
     *  called by CalendarView.get_all_filters_ordered if custom_colors set to true
     *  sets custom colors for all_filter.
     */
    _set_all_custom_colors: function() {
        var self = this;
        //console.log("self.all_filters:",self.all_filters);
        var ids = _.reject(_.keys(self.all_filters),function(num){ return num == 'undefined'; });
        //console.log("ids: ",ids);

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
        //console.log("ATTENDEES: ",Attendees, self.color_ft_field, self.color_bg_field);
        Attendees.query(['id', 'name', self.color_ft_field, self.color_bg_field]) // retrieve colors from db
            .filter([['id','in',ids]]) // id
            .all()
            .then(function (attendees){
                //console.log("attendees: ",attendees);
                for (var i=0; i<attendees.length; i++) {
                    var a = attendees[i];
                    var key = a.id;
                    kays.push(key);
                    self.all_filters[key]['color_bg'] = a[self.color_bg_field];
                    self.all_filters[key]['color_ft'] = a[self.color_ft_field];
                    self.all_filters[key]['custom_colors'] = true;
                    self.all_filters[key]['label'] = a['name'];
                };
                if (self.useContacts) {
                    self.all_filters[-1]['color_bg'] = '#C0FFE8';
                    self.all_filters[-1]['color_ft'] = '#0D0D0D';
                    self.all_filters[-1]['custom_colors'] = true;
                    self.all_filters[-1]['label'] = 'Tout le monde';
                };
                dfd.resolve();
            });

        return $.when(p).then(function(){
            return kays;
        });
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
            $.when(self._set_all_custom_colors()).then(function(kays) {
                //console.log("kays: ",kays);
                for (var i=0; i<filters.length; i++) { // doesn't work somehow. doesn't need to work apparently
                    if (filters[i].value in kays) {
                        var index = filters[i].value;
                        filters[i]['color_bg'] = self.all_filters[index].color_bg;
                        filters[i]['color_ft'] = self.all_filters[index].color_ft;
                        filters[i]['custom_colors'] = true;
                    }
                }
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
            /*for (var k in context) {
                console.log(context[k]);
                this.dataset.context[k] = context[k];
            }*/
            console.log("this.dataset.context",this.dataset.context);
            if (this.create_right && id == -1) {
                var data_template = self.get_event_data({
                    start: event.start,
                    end: event.end,
                    allDay: event.allDay,
                });
                for (var k in event.defaults) {
                    data_template[k] = event.defaults[k];
                }
                //data_template["employee_ids"] = event["context"]["default_employee_ids"];
                console.log("HAHA",event["attendees"]);
                self.open_quick_create(data_template);
                //this.do_switch_view('form', { mode: "create" });
            }
            else if (this.write_right) {
                this.do_switch_view('form', { mode: "edit" });
            } else {
                this.do_switch_view('form', { mode: "view" });
            }
        }
        else {
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
     * Override copy of parent function. Add custom colors and suffix
     * Transform OpenERP event object to fullcalendar event object
     */
    event_data_transform: function(evt) {
        //console.log("event_data_transform evt:",evt);
        var self = this;
        var date_start;
        var date_stop;
        var date_delay = evt[this.date_delay] || 1.0,
            all_day = this.all_day ? evt[this.all_day] : false,
            res_computed_text = '',
            the_title = '',
            attendees = [];

        if (!all_day) {
            date_start = time.auto_str_to_date(evt[this.date_start]);
            date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop]) : null;
        } else {
            date_start = time.auto_str_to_date(evt[this.date_start].split(' ')[0],'start');
            date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop].split(' ')[0],'start') : null;
        }

        if (this.info_fields) {
            var temp_ret = {};
            res_computed_text = this.how_display_event;
            //console.log("self.fields: ",self.fields);
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
                    else {
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
                    else {
                        throw new Error("Incomplete data received from dataset for record " + evt.id);
                    }
                }
                else {
                    temp_ret[fieldname] = value;
                }
                ///////////////////////////////////////////////////////////////////////////////////////////// this part is new
                if (!isNullOrUndef(self.fields[fieldname].__attrs["suffix"])) {
                    temp_ret[fieldname] = temp_ret[fieldname] + self.fields[fieldname].__attrs["suffix"];
                }
                ////////////////////////////////////////////////////////////////////////////////////////////////
                //console.log("temp_ret[fieldname]: ",temp_ret[fieldname]);
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

            var the_title_avatar = '';

            if (! _.isUndefined(this.attendee_people)) {
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
                               the_title_avatar += '<img title="' + _.escape(self.all_attendees[the_attendee_people]) + '" class="o_attendee_head"  \
                                                src="/web/image/' + self.avatar_model + '/' + the_attendee_people + '/image_small"></img>';
                            }
                            else {
                                if (!self.attendee_multiple && (!self.colorIsAttendee || the_attendee_people != evt[self.color_field])) {
                                    var tempColor = (self.all_filters[the_attendee_people] !== undefined) 
                                                ? self.all_filters[the_attendee_people].color
                                                : (self.all_filters[-1] ? self.all_filters[-1].color : 1);
                                    the_title_avatar += '<i class="fa fa-user o_attendee_head o_underline_color_'+tempColor+'" title="' + _.escape(self.all_attendees[the_attendee_people]) + '" ></i>';
                                }else if (self.attendee_multiple && isNullOrUndef(evt["disponible"])) {
                                    var tempColorFT, tempColorBG;
                                    var now_id;

                                    now_id = the_attendee_people;
                                    tempColorFT = self.all_filters[now_id].color_ft;
                                    tempColorBG = self.all_filters[now_id].color_bg;
                                    if (self.all_filters[now_id].is_checked && !found) {  // this will be the main color of the event
                                        evt["color_filter_id"] = now_id;
                                        found = true;
                                        if (!self.colorIsAttendee) {
                                            the_title_avatar += '<i class="of_calendar_evt_top of_calendar_attendee_box" title="' + _.escape(self.all_attendees[the_attendee_people]) + '"' +
                                                'style="background: ' + tempColorBG + '; border: 1px solid #0D0D0D; position: absolute; right: ' + icon_offset_px + 'px;" ></i>';
                                                icon_offset_px += 15;
                                        }
                                    }else{
                                        the_title_avatar += '<i class="of_calendar_evt_top of_calendar_attendee_box" title="' + _.escape(self.all_attendees[the_attendee_people]) + '"' +
                                            'style="background: ' + tempColorBG + '; border: 1px solid #0D0D0D; position: absolute; right: ' + icon_offset_px + 'px;" ></i>';
                                        icon_offset_px += 15;
                                    }
                                }else if (evt["disponible"]){
                                    var tempColorFT, tempColorBG;
                                    var now_id;

                                    now_id = the_attendee_people;
                                    tempColorFT = self.all_filters[now_id].color_ft;
                                    tempColorBG = self.all_filters[now_id].color_bg;
                                    the_title_avatar += '<i class="fa fa-search fa-lg of_calendar_evt_top of_calendar_search of_calendar_search_' + evt["index"] + '" ' +
                                                'title="' + _.escape(self.all_attendees[the_attendee_people]) + '"' +
                                                'style="background: ' + tempColorBG + ';color: ' + tempColorFT + 
                                                '; border: 1px solid #0D0D0D; position: absolute; right: ' + icon_offset_px + 
                                                'px; padding: 1px; z-index: 1000;" ></i>';
                                    /*icon_offset_px += 15;
                                    the_title_avatar += '<i class="fa fa-lg fa-search fa-border of_calendar_evt_top of_calendar_dispo_' + evt["index"] + '" title="Rechercher une intervention"' +
                                            'style="color: ' + tempColorBG + '; position: absolute; right: ' + icon_offset_px + 'px;" ></i>';*/
                                }
                            }
                        }
                        else {
                                attendee_other += _.escape(self.all_attendees[the_attendee_people]) +", ";
                        }
                    }
                );
                if (attendee_other.length>2) {
                    the_title_avatar += '<span class="o_attendee_head" title="' + attendee_other.slice(0, -2) + '">+</span>';
                }
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
            'attendee_avatars': the_title_avatar,
            'allDay': (this.fields[this.date_start].type == 'date' || (this.all_day && evt[this.all_day]) || false),
            'id': evt.id,
            'attendees':attendees,
        };
        ////////////////////////////////////////////////////////////////////////////////// This part is modified
        for (var key in self["icons"]) {
            if (evt[key]) {
                r.title = r.title + self["icons"][key];
            }
        }
        if (self.custom_colors) {
            if (evt[self.force_color_field]) {
                r.backgroundColor = evt[self.force_color_field];
                r.textColor = "#0C0C0C";
            }else if (evt[self.dispo_field]) {  // evt is phantom
                r.backgroundColor = "#7FFF00";//"rgba(127,255,0,0.5)"//
                r.textColor = "#0C0C0C";//"rgba(12,12,12,0.5)";//
            }else if (self.useContacts) {
                var index = self.get_custom_color_index(r.attendees);
                r.backgroundColor = self.all_filters[index]['color_bg'];
                r.textColor = self.all_filters[index]['color_ft'];
            }else if (self.attendee_multiple) {  // multiple attendees
                if (!isNullOrUndef(evt["color_filter_id"])) {
                    if (evt["disponible"]) {
                        //console.log("DISPO");
                        r.backgroundColor = "rgba(127,255,0,0.2)"//"#7FFF00";//
                        r.textColor = "rgba(12,12,12,0.5)";//"#0C0C0C";//
                    }else{
                        //console.log("pas dispo...");
                        r.backgroundColor = self.all_filters[ evt["color_filter_id"] ]['color_bg'];
                        r.textColor = self.all_filters[ evt["color_filter_id"] ]['color_ft'];
                    }
                }else{
                    console.log("oups! something went wrong with multiple attendees colors");
                }
                /*var now_id;
                var found = false;
                for (var i in self.now_filter_ids) {
                    now_id = self.now_filter_ids[i];
                    if (self.all_filters[now_id].is_checked && !found) {  // this will be the main color of the event
                        console.log("FOUND",now_id,self.all_filters[now_id]['color_bg'],self.all_filters[now_id]['color_ft']);
                        r.backgroundColor = self.all_filters[now_id]['color_bg'];
                        r.textColor = self.all_filters[now_id]['color_ft'];
                        found = true
                        //break;
                    }else if (self.all_filters[now_id].is_checked) {

                    }
                }*/
            }else if (evt[self.color_ft_field] && evt[self.color_bg_field]) {
                r.textColor = evt[self.color_ft_field];
                r.backgroundColor = evt[self.color_bg_field];
            }else{
                throw new Error(_t("Missing fields in calendar view definition: '" + self.color_ft_field + "' and/or '" + self.color_bg_field + "'."));
            }
            r.className = ["of_custom_color"];
            if (self.attendee_multiple) {
                for (var i=0; i<evt[self.color_field].length; i++) {
                    r.className.push("of_calendar_attendee_" + evt[self.color_field][i]);
                }
            }
            if (evt[self.selected_field]) {
                //console.log("HAHAHA event selected: ",evt);
                r.className.push("of_pulse");
            }
            if (self.display_states) {
                r.className.push("of_calendar_state_" + evt["state_int"]);
                r.borderColor = "rgba( 0, 0, 0, 0.0)"; // border to represent state
            }else{
                r.borderColor = "rgba( 0, 0, 0, 0.7)";
            }

            // events dispos
            if (evt["disponible"]) {
                r.defaults = evt["defaults"];
                r.index_dispo = evt["index"];
                r.className.push("of_calendar_dispo_" + evt["index"]);
                r.className.push("of_calendar_dispo");
            }
        }else{ // debug of odoo code
            var color_key = evt[this.color_field];
            if (typeof color_key === "object") { // make sure color_key is an integer before testing self.all_filters[color_key]
                color_key = color_key[0];
            }
            if (!self.useContacts || self.all_filters[color_key] !== undefined) {
                if (color_key) {
                    r.className = 'o_calendar_color_'+ this.get_color(color_key);
                }
            } else { // if form all, get color -1
                r.className = 'o_calendar_color_'+ (self.all_filters[-1] ? self.all_filters[-1].color : 1);
            }
        };
        ////////////////////////////////////////////////////////////////////////////////////////////
        return r;
    },
});

Sidebar.include({
    /**
     *  Override of parent function. Adds captions.
     */
    start: function() {
        this.caption = new SidebarCaption(this, this.getParent());
        return $.when(this._super(), this.caption.appendTo(this.$el));
    },
});

SidebarFilter.include({
    events: {
        'click .o_calendar_contact': 'on_click',
        'mouseover .of_calendar_filter': 'on_mouseover',
        'mouseout .of_calendar_filter': 'on_mouseout',
    },
    init: function(parent, view) {
        this._super(parent,view);
        this.filters_radio = view.filters_radio;
        //this.dfd_filters_rendered = $.Deferred();
    },
    /**
     *  Override of parent function. handles asynchronicity.
     */
    render: function() {
        var self = this;

        var fil = self.view.get_all_filters_ordered()
        //async
        $.when(fil).then(function(){ // fil is a promise
            var filters = fil.target;
            /*var filters = _.filter(fil.target, function(filter) {  disparition du filtre quand desélection??
                return _.contains(self.view.now_filter_ids, filter.value);
            });*/
            //console.log("filters!",filters);
            var filters_radio = self.filters_radio || false;
            return $.when(self.$('.o_calendar_contacts').html(QWeb.render('CalendarView.sidebar.contacts', { filters: filters, filters_radio: filters_radio })))
                .then(function(){return self.trigger_up('filters_rendered')});
        });
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
        if (this.filters_radio) {
            for(var key in all_filters){
                if (all_filters[key].value == e.target.value) {
                    all_filters[key].is_checked = e.target.checked;
                    this.current_radio_key = key;
                }else{
                    all_filters[key].is_checked = false;
                }
            };
        }else{
            all_filters[e.target.value].is_checked = e.target.checked;
        }
        this.trigger_up('reload_events');
    },
    on_mouseout: function (ev) {
        if (!this.filters_radio) {
            var class_a_pulse = ev.target.id;
            $("." + class_a_pulse).removeClass("of_pulse");
        }
    },
    on_mouseover: function (ev) {
        if (!this.filters_radio) {
            var class_a_pulse = ev.target.id;
            $("." + class_a_pulse).addClass("of_pulse");
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
