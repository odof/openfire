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

var SidebarFilter = widgets.SidebarFilter;
var Sidebar = widgets.Sidebar;
var _t = core._t;
var QWeb = core.qweb;

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

CalendarView.include({

	init: function () {
        this._super.apply(this, arguments);

        var attrs = this.fields_view.arch.attrs;
    	this.custom_colors = !isNullOrUndef(attrs.custom_colors)  && _.str.toBool(attrs.custom_colors); // true or 1 if we want to use custom colors
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

        // if we have not sidebar, (eg: Dashboard), we don't use the captions
        if (isNullOrUndef(this.options.sidebar)) {
            this.display_states = false;
        }

        //console.log("this",this);
    },
    /**
     *  go to system parameters to see if we should allow drag and drop
     */
    willStart: function() {
        var self = this
        var dfd = $.Deferred();
        var ir_config = new Model('ir.config_parameter');
        ir_config.call('get_param',['Calendar_Drag_And_Drop']).then(function(val) {
            self.draggable = _.str.toBool(val) || self.draggable; // if false in system parameters but true in view definition, make it true
            dfd.resolve();
        });
        return $.when(dfd,this._super());
    },
    /**
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
        fc.editable = this.draggable;
        return fc;
    },

    /**
     *  called by CalendarView.get_all_filters_ordered if custom_colors set to true
     *  sets custom colors for all_filter.
     */
    _set_all_custom_colors: function() {
        var self = this;
        var ids = _.reject(_.keys(self.all_filters),function(num){ return num == 'undefined'; });

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
                /*for (var i=0; i<filters.length; i++) { // doesn't work somehow. doesn't need to work apparently
                    if (filters[i].value in kays) {
                        var index = filters[i].value;
                        filters[i]['color_bg'] = self.all_filters[index].color_bg;
                        filters[i]['color_ft'] = self.all_filters[index].color_ft;
                        filters[i]['custom_colors'] = true;
                    }
                }*/
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
     *  Override of parent function. Adds custom colors to events.
     *  debug the end of parent function
     */
    event_data_transform: function(evt) {
        var self = this;
        var r = self._super.apply(self, arguments); // inherit function event_data_transform
        if (self.custom_colors) {
            if (self.useContacts) {
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
        //console.log("looks like it's working, r:",r);
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
    /**
     *  Override of parent function. handles asynchronicity.
     */
    render: function() {
        var self = this;

        var fil = self.view.get_all_filters_ordered()
        //async
        $.when(fil).then(function(){ // fil is a promise
            //console.log("fil: ",fil);
            var filters = _.filter(fil.target, function(filter) {
                return _.contains(self.view.now_filter_ids, filter.value);
            });
            //console.log("render filters :",filters);
            self.$('.o_calendar_contacts').html(QWeb.render('CalendarView.sidebar.contacts', { filters: filters }));
        });
    },
});

var SidebarCaption = Widget.extend({
    //template: 'CalendarView.sidebar.captions',

    /**
     *  called by Sidebar.start
     */
    init: function(parent, view) {
        this._super(parent);
        this.view = view;
        //console.log("this SidebarCaption: ",this);
        this.start();
    },

    start: function() {
        if (this.view.display_states) {
            this.$el.addClass("of_calendar_captions");
        };
        return $.when(this._super());
    },

    render: function () {
        var self = this;
        if (this.view.display_states) {
            $.when(new Model(this.view.dataset.model).call('get_state_int_map'))
            .then(function (states){
                //console.log("states: ", states);
                //var captions = states;
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