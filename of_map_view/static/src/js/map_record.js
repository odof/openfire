odoo.define('of_map_view.map_record', function (require) {
"use strict";

var Widget = require('web.Widget');
var data = require('web.data');
var formats = require('web.formats');
var Model = require('web.DataModel');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var map_widgets = require('of_map_view.map_widgets');
var fields_registry = map_widgets.registry;
var Qweb = core.qweb;
var mixins = core.mixins;

var MapRecord = Widget.extend({
    /**
     *  Class for the infochip of a map marker. inspired from KanbanRecord
     */
    template: 'MapView.record',
    events: {
        'click .of_map_record_action': 'on_map_record_action_clicked',
        'click .of_map_record_close': 'on_map_record_close_clicked',
    },
    /**
     *  Inits map_record
     */
    init: function(parent, marker, displayer, options) {
        //console.log('MapRecord.init arguments: ',arguments);
        this.id = marker.id;
        this._super(parent);
        this.read_only_mode = options.read_only_mode || true; // current implementation solo readonly
        this.fields = displayer.fields;
        this.many2manys = displayer.many2manys;
        this.m2m_context = displayer.m2m_context;
        this.displayer = displayer;
        this.marker = marker;
        this.highlighted = false;
        this.minimized = false;

        this.qweb = displayer.qweb;
        this.sub_widgets = [];

        var self= this;
        this.init_content(marker.record);
        //console.log('MapRecord this: ',this);
    },
    /**
     *  inits this.values ({fieldName: value, ...}),
     */
    init_content: function (record) {
        var self = this;
        this.values = {};
        _.each(record, function(v, k) {
            self.values[k] = {
                value: v.value
            };
        });
        this.record = record;
        //this.record = this.transform_record(record); <- already transformed in MapView.Marker et this.update
        var qweb_context = {
            record: this.record,
            widget: this,
            read_only_mode: this.read_only_mode,
            user_context: session.user_context,
            formats: formats,
        };
        for (var p in this) {
            //console.log("for (var p in this) { p: ",p);
            if (_.str.startsWith(p, 'map_record_')) {
                qweb_context[p] = _.bind(this[p], this);
            }
        }
        this.qweb_context = qweb_context;
        this.content = this.qweb.render('of_map_record_box', qweb_context);
        // avoid quick multiple clicks
        this.on_map_record_action_clicked = _.debounce(this.on_map_record_action_clicked, 300, true);
        //console.log('MapRecord this: ',this);
    },
    /**
     *
     */
    add_widgets: function () {
        var self = this;
        this.$("field").each(function() {
            var $field = $(this);
            var field = self.record[$field.attr("name")];
            var type = $field.attr("widget") || field.type;
            var Widget = fields_registry.get(type);
            var widget = new Widget(self, field, $field);
            widget.replace($field);
            self.sub_widgets.push(widget);
        });
    },
    /**
     * 
     */
    start: function() {
        var self = this;
        this.add_widgets();
        this.$('[tooltip]').each(function () {
            var $el = $(this);
            var tooltip = $el.attr('tooltip');
            if (tooltip) {
                $el.tooltip({
                    'html': true,
                    'title': self.qweb.render(tooltip, self.qweb_context)
                });
            }
        });
        this.postprocess_m2m_tags();
        return self._super();
    },
    /**
     *  postprocessing of fields type many2many
     *  make the rpc request for all ids/model and insert value inside .o_form_field_many2manytags fields
     */
    postprocess_m2m_tags: function() {
        //console.log("postprocess_m2m_tags: ",this.many2manys);
        var self = this;
        if (!this.many2manys.length) {
            return;
        }
        var relations = {};
        var exclude_vals = {};
        self.many2manys.forEach(function(fieldName) {
            var field = self.record[fieldName];
            var exclude_vals = self.displayer.view.m2m_options.exclude_vals || {};
            var $el = self.$('.of_map_record_field.of_map_record_field_many2manytags[name=' + fieldName + ']');
            // fields declared in the map view may not be used directly
            // in the template declaration, for example fields for which the
            // raw value is used -> $el[0] is undefined, leading to errors
            // in the following process. Preventing to add push the id here
            // prevents to make unnecessary calls to name_get
            if (! $el[0]) {
                return;
            }
            if (!relations[field.relation]) {
                relations[field.relation] = { ids: [], elements: {}, context: self.m2m_context[fieldName], exclude_vals: {}, fieldNames: []};
            }
            var rel = relations[field.relation];
            if (!rel.exclude_vals[fieldName] && exclude_vals[fieldName]) {
                rel.exclude_vals[fieldName] = exclude_vals[fieldName];
            }
            if (!rel.elements[fieldName]) {
                rel.elements[fieldName] = {};
            }
            if (!_.find(rel.fieldNames,function(n){ return n == fieldName; })) {
                rel.fieldNames.push(fieldName);
            }
            field.raw_value.forEach(function(id) {
                rel.ids.push(id);
                if (!rel.elements[fieldName][id]) {
                    rel.elements[fieldName][id] = [];
                }
                rel.elements[fieldName][id].push($el[0]);
            });
        });
        _.each(relations, function(rel, rel_name) {
            //console.log("relation: ",rel,rel_name);
            var dataset = new data.DataSetSearch(self.displayer.view, rel_name, self.displayer.view.dataset.get_context(rel.context));
            dataset.read_ids(_.uniq(rel.ids), ['name', 'color']).done(function(result) {
                _.each(rel.fieldNames, function(fName){
                    //console.log("result: ",result);
                    result.forEach(function(record) {
                        //console.log("typeof rel.exclude_vals[fName]: ",typeof rel.exclude_vals[fName]);
                        if (typeof rel.exclude_vals[fName] === 'undefined' 
                          || _.indexOf(rel.exclude_vals[fName], record.name.toLowerCase()) < 0) {  // some vals to exclude from some fields targetting this relation
                            var $tag = $('<span>')
                                .addClass('badge of_tag')
                                .append(record.name);
                            if (typeof record.color !== 'undefined'){
                                $tag.addClass('of_tag_color_' + record.color);
                            }else{
                                $tag.addClass('of_tag_color_10');
                            }
                            $(rel.elements[fName][record.id]).append($tag);
                        }
                    });
                });
            });
        });
    },
    /**
     *
     */
    renderElement: function () {
        this._super();
        var div_id = 'map_record_'+this.id;
        this.$el.addClass('of_map_record of_map_record_main');  // of_map_record used for CSS, of_map_record_main used for event binding
        this.$el.attr("id",div_id);
        //this.$el.addClass('of_map_record');
        this.$el.data('record', this);
        if (this.$el.hasClass('of_map_record_global_click') || this.$el.hasClass('of_map_record_global_click_edit')) {
            this.$el.on('click', this.proxy('on_global_click'));
        }
        this.$el.mouseover(this.on_map_record_mouseover);
        this.$el.mouseout(this.on_map_record_mouseout);
    },
    /**
     * called from MapView.reload_record
     */
    update: function (record) {
        var color_field = this.marker.group.options.color_field;
        var color_old = this.values[color_field].value;
        this.sub_widgets = [];
        var r = this.transform_record(record);
        this.init_content(r);
        this.renderElement();
        this.add_widgets();
        var color_new = this.values[color_field].value;
        if (color_old != color_new){
            this.marker.update_color(color_new);
        }
    },
    /**
     *  transforms the record so it can be used by QWeb renderer
     */
    transform_record: function(record) {
        var self = this;
        var new_record = {};
        _.each(_.extend(_.object(_.keys(this.fields), []), record), function(value, name) {
            if (value && value.value) {  // foolproofing to not try to transform an already transformed record
                new_record[name] = value;
                return;
            }
            var r = _.clone(self.fields[name] || {});
            if ((r.type === 'date' || r.type === 'datetime') && value) {
                r.raw_value = time.auto_str_to_date(value);
            } else {
                r.raw_value = value;
            }
            r.value = formats.format_value(value, r);
            new_record[name] = r;
        });
        return new_record;
    },
    /**
     *
     */
    map_record_compute_domain: function(domain) {
        return data.compute_domain(domain, this.values);
    },
    /**
     *
     */
    map_record_color: function(variable) {
        var color_field = this.marker.group.options.color_field;
        var color = this.values[color_field].value;
        return 'of_map_record_color_' + color;
    },
    /**
     *
     */
    on_global_click: function (ev) {
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
        //console.log("map_record global clicked: ");
    },
    /**
     *
     */
    on_card_clicked: function() {
        //console.log("map_record card clicked");
        this.do_open_record();
    },
    /**
     *
     */
    on_map_record_action_clicked: function(ev){
        ev.preventDefault();
        //console.log("map_record action clicked: ", ev.currentTarget); // TODO: etablir grace a fonction on_kanban_action_clicked de kanban_record.js
        var $action = $(ev.currentTarget);
        var type = $action.data('type') || 'button';

        switch (type) {
            case 'edit':
                //this.trigger_up('kanban_record_edit', {id: this.id});
                break;
            case 'open':
                this.trigger_up('map_record_open', {id: this.id});
                break;
            case 'delete':
                //this.trigger_up('kanban_record_delete', {record: this});
                break;
            case 'action':
            case 'object':
                this.trigger_up('map_do_action', $action.data());
                break;
            default:
                this.do_warn("Map: no action for type : " + type);
        }
    },
    /**
     *
     */
    on_map_record_close_clicked: function(ev){
        //console.log("map_record close clicked: ", ev.currentTarget);
        ev.preventDefault();
        this.do_close_record();
    },
    /**
     *
     */
    on_map_record_mouseover: function(ev) {
        //console.log("mouseover");
        this.do_toggle_highlighted(true);
    },
    /**
     *
     */
    on_map_record_mouseout: function(ev) {
        //console.log("mouseout");
        this.do_toggle_highlighted(false);
    },
    /**
     *	Handles signal to switch to the form view of a record. Triggers the view's custom event
     */
    do_open_record: function() {
        this.trigger_up('map_record_open', {id: this.id});
    },
    /**
     *	Remove the record from the displayer. doesn't remove the marker
     */
    do_close_record: function() {
        this.displayer.do_highlight_record(this.id,false,true);
        this.marker.do_toggle_selected(false);
        delete this.displayer.records[this.id];  // delete the record from the displayer
        this.destroy(); // destroy the widget map_record
    },
    /**
     *	Handles signal to highlight or downplay the map_record. the displayer does the connection
     *
     *	@param {Boolean} on true for highlighting, false for downplaying.
     */
    do_toggle_highlighted: function(on) {
        //console.log('MapRecord.do_toggle_highlighted on: ',on);
        if (_.isBoolean(on)) {
            this.highlighted = !this.highlighted;
            this.displayer.do_highlight_record(this.id,on);
        }else{
            this.highlighted = !this.highlighted;
            this.displayer.do_highlight_record(this.id,this.highlighted);
        }
    },
    });

return MapRecord;
});