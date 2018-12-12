odoo.define('of_calendar.calendar_view', function (require) {
"use strict";
/*---------------------------------------------------------
 * OpenFire calendar
 *---------------------------------------------------------*/

var core = require('web.core');
var CalendarView = require('web_calendar.CalendarView');
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

    init: function () {
        var self = this;
        this._super.apply(this, arguments);

        var attrs = this.fields_view.arch.attrs;
        this.working_hours = !isNullOrUndef(attrs.working_hours) && attrs.working_hours; // "parent" or "attendees"
        this.filters_radio = !isNullOrUndef(attrs.filters_radio) && _.str.toBool(attrs.filters_radio); // true or 1 if we want filters to be of type radio
        this.custom_colors = !isNullOrUndef(attrs.custom_colors) && _.str.toBool(attrs.custom_colors); // true or 1 if we want to use custom colors
        this.show_first_evt = !isNullOrUndef(attrs.show_first_evt) && _.str.toBool(attrs.show_first_evt); // true or 1 if we want to jump to the first event
        this.jump_to = !isNullOrUndef(attrs.jump_to) && attrs.jump_to; // "first" or "selected"
        this.dispo_field = attrs.dispo_field;
        this.force_color_field = attrs.force_color_field;
        this.selected_field = attrs.selected_field;

        this.color_ft_field = attrs.color_ft_field;
        this.color_bg_field = attrs.color_bg_field;
        if (this.custom_colors && !(attrs.color_ft_field && attrs.color_bg_field)) {
            throw new Error(_t("Calendar views with 'custom_colors' attribute set to true need to define both 'color_ft_field' and 'color_bg_field' attributes."));
        }
        this.attendee_model = attrs.attendee_model;
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
     *  go to system parameters to see if we should allow drag and drop. Inits working hours field if needed
     */
    willStart: function() {
        var self = this;
        var dfd = $.Deferred();
        var dfd2 = $.Deferred();
        var ir_config = new Model('ir.config_parameter');
        ir_config.call('get_param',['Calendar_Drag_And_Drop']).then(function(val) {
            self.draggable = _.str.toBool(val) || self.draggable; // if false in system parameters but true in view definition, make it true
            dfd.resolve();
        });

        this.init_working_hours_fields()
        .then(function () {
            self.set_min_max_time()
            .then(function() {
                dfd2.resolve();
            });
        });

        return $.when(dfd,dfd2,this._super());
    },
    /**
     * override copy of parent function. Sets up first event to be displayed. Handles radio filters
     */
    _do_search: function (domain, context, _group_by) {
        var self = this;
        if (! self.all_filters) {
            self.all_filters = {};
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

                var current_event_source = self.event_source;
                    var event_domain = self.get_range_domain(domain, start, end);
                    if (self.useContacts && (!self.all_filters[-1] || !self.all_filters[-1].is_checked)) {
                        var partner_ids = $.map(self.all_filters, function(o) { if (o.is_checked) { return o.value; }});
                        if (!_.isEmpty(partner_ids)) {
                            event_domain = new data.CompoundDomain(
                                event_domain,
                                [[self.attendee_people, 'in', partner_ids]]
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
                    self.first_evt = events.length > 0 && events[0] || undefined;
                    if (!isNullOrUndef(self.jump_to) && !isNullOrUndef(self.first_evt)) {
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
                        //////////////////////////////////////////////////////////////////////////////////

                        if (self.sidebar) {
                            self.sidebar.filter.render();

                            events = $.map(events, function (e) {
                                var key = color_field.type == "selection" ? e[self.color_field] : e[self.color_field][0];
                                if (_.contains(self.now_filter_ids, key) &&  self.all_filters[key].is_checked) {
                                    return e;
                                }
                                return null;
                            });
                        }
                    }

                    var all_attendees = $.map(events, function (e) { return e[self.attendee_people]; });
                    all_attendees = _.chain(all_attendees).flatten().uniq().value();

                    self.all_attendees = {};
                    if (self.avatar_title !== null) {
                        new Model(self.avatar_title).query(["name"]).filter([["id", "in", all_attendees]]).all().then(function(result) {
                            _.each(result, function(item) {
                                self.all_attendees[item.id] = item.name;
                            });
                        }).done(function() {
                            return self.perform_necessary_name_gets(events).then(callback);
                        });
                    }
                    else {
                        _.each(all_attendees,function(item){
                                self.all_attendees[item] = '';
                        });
                        return self.perform_necessary_name_gets(events).then(callback);
                    }
                });
            },
            eventDataTransform: function (event) {
                return self.event_data_transform(event);
            },
        };
        this.$calendar.fullCalendar('addEventSource', this.event_source);
    },
    /**
     *  render states caption if display_states in attributes
     */
    init_working_hours_fields: function () {
        var self = this;
        var dfd = $.Deferred();
        var model;
        if (this.attendee_model && this.working_hours == "attendees") {
            model = new Model(this.attendee_model);
        }else if (this.working_hours == "parent" && this.parent_model) { // only in One2many
            model = new Model(this.parent_model);
        }

        if (!isNullOrUndef(model)) {
            $.when(model.call('get_working_hours_fields'))
            .then(function (res){
                self.working_hours_fields = {};

                self.working_hours_fields.mor_start_field = res["morning_start_field"];
                self.working_hours_fields.mor_end_field = res["morning_end_field"];
                self.working_hours_fields.aft_start_field = res["afternoon_start_field"];
                self.working_hours_fields.aft_end_field = res["afternoon_end_field"];

                dfd.resolve();
            });

        }else{
            this.working_hours_fields = undefined;
            dfd.resolve();
        }
        return $.when(dfd);//.then(function(){console.log("YAY: ",self.working_hours_fields)});
    },
    /**
     *  Sets up this.minTime and this.maxTime
     */
    set_min_max_time: function() {
        var self = this;
        var dfd = $.Deferred();
        if (isNullOrUndef(this.working_hours_fields)) {
            dfd.resolve();
        }else if (this.attendee_model && this.working_hours == "attendees") { // working hours are stored in attendees model
            var model = new Model(this.attendee_model);
            var ms = this.working_hours_fields.mor_start_field;
            var me = this.working_hours_fields.mor_end_field;
            var as = this.working_hours_fields.aft_start_field;
            var ae = this.working_hours_fields.aft_end_field;
            var fields = [ms, me, as, ae, "tz", "tz_offset"];
            self.working_hours = {};
            model.query(fields)
            .all()
            .then(function (res) {
                /*
                prendre toutes les horaires, les mettres en UTC, les comparer pour avoir le min et max
                mettre le min et max en localetime pour set minTime et maxTime (plage horaire affichée du calendrier)
                */
                //console.log("res: ",res);
                var date_today = new Date(); // today by default
                var str_UTC = date_today.toUTCString(); // str UTC
                var str_prefix = str_UTC.substring(0,17); // str UTC without time
                var str_suffix = str_UTC.substring(25); // str UTC without time (eg GMT+0100)
                var descript = {type: "float_time"}; // to format float into hh:mm
                var minTime, minUTC, maxTime, maxUTC, min_time, max_time;

                _.each(res, function(record){
                    min_time = formats.format_value(record[ms],descript) + ":00"; // time formatted hh:mm:ss
                    max_time = formats.format_value(record[ae],descript) + ":00"; // time formatted hh:mm:ss
                    record.min_UTC = str_prefix + min_time + str_suffix + record.tz_offset;
                    record.max_UTC = str_prefix + max_time + str_suffix + record.tz_offset;
                    record.min_date_UTC = new Date(record.min_UTC);
                    record.max_date_UTC = new Date(record.max_UTC);

                    if (isNullOrUndef(minUTC)) minUTC = record.min_date_UTC; // set min
                    if (record.min_date_UTC.getTime() < minUTC.getTime()) minUTC = record.min_date_UTC; // update min
                    if (isNullOrUndef(maxUTC)) maxUTC = record.max_date_UTC; // set max
                    if (record.max_date_UTC.getTime() > maxUTC.getTime()) maxUTC = record.max_date_UTC; // update max

                    self.working_hours[record.id] = { // keep a trace
                        mor_start: min_time,
                        mor_end: formats.format_value(record[me],descript) + ":00",
                        aft_start: formats.format_value(record[as],descript) + ":00",
                        aft_end: max_time,
                        tz: record["tz"],
                        tz_offset: record["tz_offset"],
                        str_suffix: " GMT" + record["tz_offset"],
                    }
                });
                if (isNullOrUndef(minUTC)) minUTC = new Date(str_prefix + "00:00:00" + str_suffix ); // if no records
                if (isNullOrUndef(maxUTC)) maxUTC = new Date(str_prefix + "00:00:00" + str_suffix ); // if no records
                minTime = minUTC.toLocaleTimeString(); // local time format hh:mm:ss
                maxTime = maxUTC.toLocaleTimeString(); // local time format hh:mm:ss

                self.minTime = minTime;
                self.maxTime = maxTime;
                //console.log("self.minTime: ",self.minTime);
                dfd.resolve();
            });
        }else if (this.working_hours == "parent" && this.parent_model) { // only in O2M case
            var date_today = new Date(); // today by default
            var str_UTC = date_today.toUTCString(); // str UTC
            var str_prefix = str_UTC.substring(0,17); // str UTC without time
            var str_suffix = "";
            if (this.parent_values["tz_offset"]) str_suffix = str_UTC.substring(25) + this.parent_values["tz_offset"]; // str UTC without time (eg GMT+0100)
            var descript = {type: "float_time"}; // to format float into hh:mm
            var ms = this.working_hours_fields.mor_start_field;
            var ae = this.working_hours_fields.aft_end_field;
            var min_time = formats.format_value(this.parent_values[ms] - 0.5,descript) + ":00"; // mintime UTC minus 1h format hh:mm:ss
            var max_time = formats.format_value(this.parent_values[ae] + 0.5,descript) + ":00"; // maxtime UTC plus 1h format hh:mm:ss
            var min_UTC = str_prefix + min_time + str_suffix; // str UTC
            var max_UTC = str_prefix + max_time + str_suffix; // str UTC
            var min_date_UTC = new Date(min_UTC); // date UTC
            var max_date_UTC = new Date(max_UTC); // date UTC
            var minTime = min_date_UTC.toLocaleTimeString(); // local time format hh:mm:ss
            var maxTime = max_date_UTC.toLocaleTimeString(); // local time format hh:mm:ss

            self.minTime = minTime;
            self.maxTime = maxTime;
            dfd.resolve();
        }else{
            dfd.resolve();
        }
        return $.when(dfd);
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
     *  update drag n drop
     */
    get_fc_init_options: function () {
        var fc = this._super();
        var self = this;
        fc.editable = this.draggable;
        fc.minTime = this.minTime;
        fc.maxTime = this.maxTime;
        // callback
        fc.eventAfterAllRender = function(view) {
            if (!isNullOrUndef(self.first_evt)) {
                self.on_event_after_all_render();
            }
        };
        return fc;
    },
    /**
     *  Jumps to first event rather than current day
     */
    on_event_after_all_render: function() {
        var self = this;
        if (!isNullOrUndef(self.first_evt) && !self.first_jump) { // only jump once, else we can't navigate through the calendar
            self.first_jump = true;
            var date_tmp = new Date(self.first_evt[self.date_start]);
            self.$calendar.fullCalendar('gotoDate', date_tmp);
        }
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
        Attendees.query(['id', self.color_ft_field, self.color_bg_field]) // retrieve colors from db
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
                };
                if (self.useContacts) {
                    self.all_filters[-1]['color_bg'] = '#C0FFE8';
                    self.all_filters[-1]['color_ft'] = '#0D0D0D';
                    self.all_filters[-1]['custom_colors'] = true;
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
                var MAX_ATTENDEES = 3;
                var attendee_showed = 0;
                var attendee_other = '';

                _.each(temp_ret[this.attendee_people],
                    function (the_attendee_people) {
                        attendees.push(the_attendee_people);
                        attendee_showed += 1;
                        if (attendee_showed<= MAX_ATTENDEES) {
                            if (self.avatar_model !== null) {
                                       the_title_avatar += '<img title="' + _.escape(self.all_attendees[the_attendee_people]) + '" class="o_attendee_head"  \
                                                        src="/web/image/' + self.avatar_model + '/' + the_attendee_people + '/image_small"></img>';
                            }
                            else {
                                if (!self.colorIsAttendee || the_attendee_people != temp_ret[self.color_field]) {
                                        var tempColor = (self.all_filters[the_attendee_people] !== undefined) 
                                                    ? self.all_filters[the_attendee_people].color
                                                    : (self.all_filters[-1] ? self.all_filters[-1].color : 1);
                                        the_title_avatar += '<i class="fa fa-user o_attendee_head o_underline_color_'+tempColor+'" title="' + _.escape(self.all_attendees[the_attendee_people]) + '" ></i>';
                                }//else don't add myself
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
            'attendees':attendees
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
            }else if (evt[self.color_ft_field] && evt[self.color_bg_field]) {
                r.textColor = evt[self.color_ft_field];
                r.backgroundColor = evt[self.color_bg_field];
            }else{
                throw new Error(_t("Missing fields in calendar view definition: '" + self.color_ft_field + "' and/or '" + self.color_bg_field + "'."));
            }
            r.className = ["of_custom_color"];
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
    init: function(parent, view) {
        this._super(parent,view);
        this.filters_radio = view.filters_radio;
    },
    /**
     *  Override of parent function. handles asynchronicity.
     */
    render: function() {
        var self = this;

        var fil = self.view.get_all_filters_ordered()
        //async
        $.when(fil).then(function(){ // fil is a promise
            var filters = _.filter(fil.target, function(filter) {
                return _.contains(self.view.now_filter_ids, filter.value);
            });
            var filters_radio = self.filters_radio || false;
            self.$('.o_calendar_contacts').html(QWeb.render('CalendarView.sidebar.contacts', { filters: filters, filters_radio: filters_radio }));
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