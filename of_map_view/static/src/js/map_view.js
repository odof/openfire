odoo.define('of_map_view.MapView', function (require) {
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
var Sidebar = require('web.Sidebar');

/**
 *	TODO: add warning when using OSM tile server
 */

var TILE_SERVER_ADDR = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
// ratio to get marker width out of marker height
var H2W_RATIO = 1.64

var ROUTE_AVAILABLE_COLORS = [
    '#008080', '#ff6347', '#6a5acd', '#2e8b57', '#8b4513', '#ff1493', '#00bfff', '#ff4500', '#ff8c00',
    '#36dee6', '#d23d56', '#61c26e', '#c36cc8', '#9bb03f', '#6678dc', '#d49c3b', '#543789', '#45bc8d',
    '#c9467e', '#6a8c3e', '#852768', '#a67e3a', '#8687d0', '#c35d2f', '#d774b3', '#882f1c', '#e07c60',
    '#0066cc', '#ff0000', '#00ff00', '#0000ff', '#ff00ff', '#00ffff', '#ffff00', '#d2691e', '#7cfc00',
    '#b44f65', '#bf5055'];
var DEFAULT_POLYLINE_COLOR = '#0066cc';
var DEFAULT_TOUR_START_STOP_COLOR = '#333333';
var DEFAULT_ADDITIONNAL_RECORD_COLOR = '#25aa22';

var Class = core.Class;
var _t = core._t;
var _lt = core._lt;
var qweb = core.qweb;

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

var MapView = View.extend({
    template: 'MapView',
    display_name: _lt('Map'),
    icon: 'fa fa-map-marker',
    view_type: "map",
    className: "of_map_view",
    _model: null,
    defaults: _.extend({}, View.prototype.defaults, {
        // records can be selected one by one
        selectable: true,
        // list rows can be deleted
        deletable: false,
        // whether the column headers should be displayed
        header: true,
        // display addition button, with that label
        addable: _lt("Create"),
        // whether the list view can be sorted, note that once a view has been
        // sorted it can not be reordered anymore
        sortable: true,
        // whether the view rows can be reordered (via vertical drag & drop)
        reorderable: true,
        action_buttons: true,
        // whether the editable property of the view has to be disabled
        disable_editable_mode: false,
        auto_search: false, // the search is done when the map is attached. See MapView.Map.on_map_attached. Apparently not taken into account D:
        dummy_option: 'dummy_string' // for testing
    }),
    custom_events: {
        'map_record_open': 'open_record',
        'map_do_action': 'open_action',
    },
    /**
     *
     */
    init: function() {
        //console.log("MapView.init: ",arguments);
        this._super.apply(this, arguments);

        this.qweb = new QWeb(session.debug, {_s: session.origin}, false);

        this._model = new Model(this.dataset.model);
        this.min_width = this.fields_view.arch.attrs.min_width;
        this.min_height = this.fields_view.arch.attrs.min_height;
        this.lat_field = this.fields_view.arch.attrs.latitude_field;
        this.lng_field = this.fields_view.arch.attrs.longitude_field;
        this.number_field = this.fields_view.arch.attrs.number_field;
        this.hide_pager = this.fields_view.arch.attrs.hide_pager || '0';
        this.geojson_data = this.fields_view.arch.attrs.geojson_data || '0';
        this.endpoint_geojson_data = this.fields_view.arch.attrs.endpoint_geojson_data;
        this.name = "" + this.fields_view.arch.attrs.string;
        this.legend_context = JSON.parse(this.fields_view.arch.attrs.legend_context || "{}");
        this.fields = this.fields_view.fields;
        this.fields_keys = _.keys(this.fields_view.fields);
        if (this.dataset.get_context().eval().additional_records) {
            // Data that we want to display on the map with a fake record marker.
            this.additional_records = JSON.parse(this.dataset.get_context().eval().additional_records);
        } else {
            this.additional_records = false;
        }
        if (this.dataset.get_context().eval().additional_record_geojson_data) {
            // Data that we want to display on the map with fake routes to/from the fake record marker.
            this.additional_record_geojson_data = JSON.parse(this.dataset.get_context().eval().additional_record_geojson_data);
        } else {
            this.additional_record_geojson_data = false;
        }
        this.grouped = undefined;  // later implementation
        this.group_by_field = undefined;  // later implementation
        this.default_group_by = this.fields_view.arch.attrs.default_group_by;  // later implementation

        // the view's number of records per page (|| section), defaults to 80
        this._limit = (this.options.limit ||
                       this.defaults.limit ||
                       (this.getParent().action || {}).limit ||
                       parseInt(this.fields_view.arch.attrs.limit, 10) ||
                       80);
        // the index of the first displayed record (starting from 1)
        this.current_min = 1;
        this.current_max = this._limit + this.current_min;

        this.data = undefined;

        this.search_orderer = new utils.DropMisordered();

        this.many2manys = this.fields_view.many2manys || [];
        this.m2m_context = {};
        this.m2m_options = {};

        this.map = null;
        this.nondisplayable_records = [];
        this.records = [];

        // generate random id
        this.map_id = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

        //console.log("MapView.init this: ",this);
    },
    /**
     *  Inits record fields. latitude and longitude to place records on the map. color when needed
     *  See map_controls and map_records
     */
    init_record_options: function() {
        //console.log("MapView.init_record_fields");
        var self = this;
        var dfd = $.Deferred();
        var p = dfd.promise();
        this.record_options = {};
        this.record_options.latitude_field = this.lat_field;
        this.record_options.longitude_field = this.lng_field;
        this.record_options.number_field = this.number_field;
        this.record_options.geojson_data = this.geojson_data;
        this.record_options.endpoint_geojson_data = this.endpoint_geojson_data;
        this.record_options.additional_records = this.additional_records;
        this.record_options.additional_record_geojson_data = this.additional_record_geojson_data;
        this.record_options.color_field = this.fields_view.arch.attrs.color_field;
        this.record_options.draw_routes = this.fields_view.arch.attrs.draw_routes || '0';
        this.record_options.connect_markers = this.fields_view.arch.attrs.connect_markers || '0';
        this.record_options.remove_routes = this.fields_view.arch.attrs.remove_routes || '0';
        var ir_config = new Model('ir.config_parameter');
        ir_config.call('get_param', ['Map_Marker_Size']).then(function(res){
            if (['x-small', 'small', 'medium', 'large'].includes(res)) {
                self.record_options.marker_size = res;
            }
            dfd.resolve();
        });

        return $.when(p);
    },
    init_displayer_options: function() {
        this.displayer_options = {};
        this.displayer_options.qweb = this.qweb;
        this.displayer_options.legends = [];
        this.displayer_options.context = this.legend_context;
        if (this.fields_view.arch.attrs.color_field) {
            var legend_method = this.fields_view.arch.attrs.force_legend_method || 'get_color_map';
            var legend_color = {
                name: 'legend_color',
                method: legend_method,
                template: 'MapView.legend.colors'
            };
            this.displayer_options.legends.push(legend_color);
        }
    },
    /**
     * Method called between init and start. Performs asynchronous calls required by start.
     */
    willStart: function() {
        //console.log("MapView.willStart: ",arguments);
        var self = this;

        // add qweb templates
        for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
            var child = this.fields_view.arch.children[i];
            if (child.tag === "templates") {
                map_utils.transform_qweb_template(child, this.fields_view, this.many2manys, this.m2m_options);
                // transform_qweb_template(), among other things, identifies and processes the
                // many2manys. Unfortunately, it modifies the fields_view in place and, as
                // the fields_view is stored in the JS cache, the many2manys are only identified the
                // first time the fields_view is processed. We thus store the identified many2manys
                // on the fields_view, so that we can retrieve them later. A better fix would be to
                // stop modifying shared resources in place.
                this.fields_view.many2manys = this.many2manys;
                this.qweb.add_template(utils.json_node_to_xml(child));
                break;
            } else if (child.tag === 'field') {
                var ftype = child.attrs.widget || this.fields[child.attrs.name].type;
                if(ftype === "many2many" && "context" in child.attrs) {
                    this.m2m_context[child.attrs.name] = child.attrs.context;
                }
            }
        }
        this.init_displayer_options();

        var rendered_prom = this.$el.html(qweb.render(this.template, {widget: this})).promise();
        var options = {};
        if (!this.options.map_center_and_zoom) { // the map will use default center and zoom config, found in ir.config_parameter
            options.map_center_and_zoom = true;
        }
        if (!this.options.tile_server_addr) { // the map will use default tile server config, found in ir.config_parameter
            options.tile_server_addr = true;
        }
        var record_option_inited = this.init_record_options();

        var q = true;
        if (options.map_center_and_zoom || options.tile_server_addr) {
            q = this.get_default_map_config(options).promise();
        }
        return $.when(this._super(), rendered_prom, record_option_inited, q);
    },
    /**
     * Method called after rendering. Mostly used to bind actions, perform asynchronous
     * calls, etc...
     *
     * By convention, this method should return an object that can be passed to $.when() 
     * to inform the caller when this widget has been initialized.
     *
     * @returns {jQuery.Deferred or any}
     */ 
    start: function() {
        //console.log("MapView.start: ",arguments);
        this.$el.addClass(this.fields_view.arch.attrs.class || "o_map_view");
        var options = {center: this.options.map_center_and_zoom[0], zoom: this.options.map_center_and_zoom[1]};
        if (this.options.tile_server_addr) options.tile_server_addr = this.options.tile_server_addr;
        if (this.record_options.marker_size) options.marker_size = this.options.marker_size;
        options.displayer_options = this.displayer_options;
        options.container_id = this.map_id;
        var args = {view: this, options};
        //console.log("map options: ",options);
        this.map = new MapView.Map(args);

        return this._super();
    },
    /**
     * adds (if necessary) domain to only search for displayable records. Return new domain
     *
     * @returns {Array} new domain
     */
    _transform_domain: function(domain) {
        //console.log("_transform_domain: ",domain);
        // @TODO: make precision dynamic
        //var d1 = ["precision", "in", ["manual","high","medium","low"]];
        var d2 = [this.lat_field, '!=', 0.0];
        var d3 = [this.lng_field, '!=', 0.0];
        //var a_concat_1 = [ d1 ];
        var a_concat = [ '|', d2, d3 ];
        if (!domain || !domain.length) {
            return a_concat;
        }
        for (var i=0; i<domain.length; i++) {
            if (JSON.stringify(domain[i]) === JSON.stringify(d2)) {
                return domain;
            }
        }
        return domain.concat(a_concat);
    },
    /**
     * Handler for the result of eval_domain_and_context, actually perform the searching by calling private method
     */
    do_search: function (domain, context, group_by) {
        //console.log("MapView.do_search: ",arguments);
        var self = this;
        // don't take into account nondisplayable records
        this.domain = this._transform_domain(domain);
        this.context = context;
        this.group_by = group_by;
        // only do the search if the map is attached. Workaround the auto_search option not working properly.
        if (this.map.is_attached()) {
            //console.log('this.map.is_attached()');
            this._do_search(this.domain, context, group_by);
        }else{
            //console.log('do_search not done, map not attached');
        }
    },
    /**
     *  private method to perform a search
     */
    _do_search: function (domain, context, group_by) {
        //console.log("MapView._do_search: ",arguments);
        var self = this;
        this.nondisplayable_records = [];
        var group_by_field = group_by && group_by[0] || this.default_group_by;
        var field = this.fields[group_by_field];
        var options = {};
        var fields_def;
        if (field === undefined) {
            fields_def = data_manager.load_fields(this.dataset).then(function (fields) {
                self.fields = fields;
                field = self.fields[group_by_field];
            });
        }
        var load_def = $.when(fields_def).then(function() {
            var grouped_by_m2o = field && (field.type === 'many2one');
            options = _.extend(options, {
                search_domain: domain,
                search_context: context,
                group_by_field: group_by_field,
                grouped: group_by && group_by.length || self.default_group_by,
                grouped_by_m2o: grouped_by_m2o,
                relation: (grouped_by_m2o ? field.relation : undefined),
            });
            return options.grouped ? console.log("group_by not implemented yet!") : self.load_records(self.current_min-1);
        });
        return this.search_orderer
            .add(load_def)
            .then(function (data) {
                _.extend(self, options);
                if (options.grouped) {
                    /*var new_ids = _.union.apply(null, _.map(data.groups, function (group) {
                        return group.dataset.ids;
                    }));
                    self.dataset.alter_ids(new_ids);*/  // later implementation
                    console.log("group_by not implemented yet!");
                }
                self.data = data;
            });
    },
    /**
     *  Loads the records. calls this.get_records when needed
     */
    load_records: function (offset=0, origin="search") {
        //console.log("MapView.load_records: ",arguments);
        var self = this;
        var dfd_1 = $.Deferred();
        var dfd_2 = $.Deferred();

        // Reloads additional records when loading records (usefull when additional records depend of records, like in tour lines)
        var additional_records = self.dataset.get_context().eval().additional_records;
        if (additional_records) {
            // Data that we want to display on the map with a fake record marker.
            self.additional_records = JSON.parse(additional_records);
        } else {
            self.additional_records = false;
        }

        self.record_options.additional_records = self.additional_records;

        if (origin === "search" || origin === "reload") {  // get records from datasbase
            dfd_1 = this.get_records(offset, origin)
                    .then(function(){
                        self.map.reset_layer_groups();
                    })
                    .then(function() {
                        if (self.records.length || self.record_options.additional_records !== undefined) {
                            // if there is no records to display but there is an additional record, display it
                            self.map.add_layer_group(self.records,self.record_options);
                            self.map.nocontent_displayer.do_hide();
                        }else{
                            self.map.nocontent_displayer.do_show();
                        }
                        self.map.nocontent_displayer.update_content();
                    });
        }else if (this.need_get_records()) {  // get records from database, origin == pager
            dfd_1 = this.get_records(offset, origin)
                    .then(function(){
                        var all_ids = self.records.map(x => x.id || undefined);
                        var actual_ids = all_ids.filter(function(el){return !!el;})

                        self.dataset.add_ids(actual_ids);
                        self.dataset._length = all_ids.length;  // workaround some bug in odoo code to keep pager with right values
                        var layer_group = self.map.layer_groups[self.map.current_layer_group_index];
                        layer_group.update_records(self.records);
                        layer_group.do_show_range(offset,false,true,true);
                    });
        }else{  // records already loaded, origin == pager
            var all_ids = self.records.map(x => x.id || undefined);
            var actual_ids = all_ids.filter(function(el){return !!el;})

            self.dataset.add_ids(actual_ids);
            self.dataset._length = all_ids.length;  // workaround some bug in odoo code to keep pager with right values
            var layer_group = self.map.layer_groups[self.map.current_layer_group_index];
            layer_group.do_show_range(offset,false,true,true);
            dfd_1.resolve();
        }

        this.do_push_state({
            min: offset + 1,
            limit: this._limit
        });

        return $.when(dfd_1)
            .then(function(){
                self.update_pager(offset + 1);
            });
    },
    /**
     *  Checks if there is at least one record that we need to get from database
     */
    need_get_records: function() {
        for (var i=this.current_min-1; i<this.current_max; i++) {
            if (this.records[i] == undefined) {
                return true;
            }
        }
    },
    /**
     *  get records from database and update self.records
     *
     *  @return {jQuery.Deferred}
     */
    get_records: function (offset=0, origin="search") {
        //console.log("MapView.get_records: ",arguments);
        var self = this;
        var options = {
            'limit': this._limit,
            'offset': offset,
            'domain': this.domain,
            'context': this.context,
        };
        var read_fields = this.fields_keys.concat(['__last_update']);
        return this.dataset.read_slice(read_fields, options)
                .then(function(records){
                    var lgt = self.dataset.size();
                    if (origin === "search" || origin === "reload") {
                        self.records = new Array(lgt);
                    }
                    for (var i = 0; i < records.length; ++i) {
                        var le_index = i + offset;
                        if (self.records[le_index] == undefined && records[i] != undefined) {
                            self.records[le_index] = records[i];
                            //console.log("new record in list");  // tu peux décommenter ça pour tes tests ;)
                        }
                    }
                    return $.when();
                });
    },
    /**
     *	
     *
     *	@param {Boolean} options.map_center_and_zoom true if we need to query default map center and zoom data
     *	@param {Boolean} options.tile_server_addr true if we need to query default tile server address
     *  @return {jQuery.Deferred} 
     */
    get_default_map_config: function (options) {
        //console.log("MapView.get_default_map_config: ",options);
        var self = this;
        var ir_config = new Model('ir.config_parameter');
        var dfd_1 = $.Deferred();
        var dfd_2 = $.Deferred();
        var p1 = dfd_1.promise();
        var p2 = dfd_2.promise();

        if (options.map_center_and_zoom) {
            //console.log('getting map center and zoom');
            self.options.map_center_and_zoom = [];
            ir_config.call('get_param',['Map_Default_Center_Latitude']).then(function(lat) {
                self.options.map_center_and_zoom[0] = [];
                self.options.map_center_and_zoom[0][0] = lat;
                return ir_config.call('get_param',['Map_Default_Center_Longitude']);
            }).then(function(lng) {
                self.options.map_center_and_zoom[0][1] = lng;
                return ir_config.call('get_param',['Map_Default_Zoom']);
            }).then(function(zoom) {
                self.options.map_center_and_zoom[1] = zoom;
                //console.log('map_center_and_zoom: ',self.options.map_center_and_zoom);
                dfd_1.resolve();
            });
        }else{
            dfd_1.resolve();
        }
        if (options.tile_server_addr) {
            //console.log('getting tile server address');
            ir_config.call('get_param',['Map_Tile_Server_Address']).then(function(res){
                if (res !== 'undefined') {
                    self.options.tile_server_addr = res;
                    //console.log("tile server address should be: ",res);
                }
                dfd_2.resolve();
            });
        }else{
            dfd_2.resolve();
        }

        return $.when(p1,p2);
    },
    /**
     * Handles signal for the addition of a new record (can be a creation,
     * can be the addition from a remote source, ...)
     * Not currently used, for later implementations
     *
     * The default implementation is to switch to a new record on the form view
     */
    do_add_record: function () {
        //console.log("MapView.do_add_record");
        this.select_record(null);
    },
    /**
     *  Handles signal to open the form view of a record
     */
    open_record: function (event, options) {
        //console.log("MapView.open_record: ",arguments);
        if (this.dataset.select_id(event.data.id)) {
            this.do_switch_view('form', options);
        } else {
            // We are using fake records markers to display additional records on the map with the other reals
            // markers based on real records of the O2M. So there are fakes ids on the record that are not in the dataset.
            // We don't want to display the warning message in this case.
            if (event.target.options != undefined && (event.target.options.additional_records === undefined || event.target.options.additional_records[0].id != event.data.id)) {
                this.do_warn("Map: could not find id#" + event.data.id);
            }
            // Fake records start and stop markers
            if (event.target.options === undefined || event.target.record === undefined || (event.target.record.number === 'start' || event.target.record.number === 'stop')) {
                return;
            }
        }
    },
    /**
     *  Handles signal to open an action
     */
    open_action: function (event) {
        var self = this;
        if (event.data.context) {
            event.data.context = new data.CompoundContext(event.data.context)
                .set_eval_context({
                    active_id: event.target.id,
                    active_ids: [event.target.id],
                    active_model: this.model,
                });
        }
        //console.log("event data:",event.data);
        this.do_execute_action(event.data, this.dataset, event.target.id, _.bind(self.reload_record, this, event.target));
    },
    reload_record: function (record) {
        var self = this;
        this.dataset.read_ids([record.id], this.fields_keys.concat(['__last_update'])).done(function(records) {
            if (records.length) {
                record.update(records[0]);
                record.postprocess_m2m_tags();
            } else {
                record.destroy();
            }
        });
    },
    /**
     *  postprocessing of fields type many2many
     *  make the rpc request for all ids/model and insert value inside .of_map_field_many2manytags fields
     */
    postprocess_m2m_tags: function(records) {
        records = records instanceof Array ? records : [records];
        _.each(records, function(record){
            record.postprocess_m2m_tags();
        });
    },
    /**
     * Instantiate and render the sidebar.
     * Sets this.sidebar
     * @param {jQuery} [$node] a jQuery node where the sidebar should be inserted
     * $node may be undefined, in which case the ListView inserts the sidebar in
     * this.options.$sidebar or in a div of its template
     **/
    render_sidebar: function($node) {
        if (!this.sidebar && this.options.sidebar) {
            this.sidebar = new Sidebar(this, {editable: this.is_action_enabled('edit')});
            if (this.fields_view.toolbar) {
                this.sidebar.add_toolbar(this.fields_view.toolbar);
            }

            $node = $node || this.options.$sidebar;
            this.sidebar.appendTo($node);

            // Hide the sidebar by default (it will be shown as soon as a record is selected)
            this.sidebar.do_hide();
        }
    },
    /**
     * Instantiate and render the pager and add listeners on it.
     * Set this.pager
     * @param {jQuery} [$node] a jQuery node where the pager should be inserted
     * $node may be undefined, in which case the ListView inserts the pager into this.options.$pager
     */
    render_pager: function($node, options) {
        //console.log("MapView.render_pager: ",arguments);
        if (!this.pager && this.options.pager) {
            this.pager = new Pager(this, this.dataset.size(), 1, this._limit, options);
            this.pager.appendTo($node || this.options.$pager);
            var self = this;

            this.pager.on('pager_changed', this, function (new_state) {
                var layer_group = self.map.layer_groups[self.map.current_layer_group_index];
                self.current_min = new_state.current_min;
                self.current_max = self.pager.state.current_max;
                self._limit = new_state.limit;
                layer_group._limit = new_state.limit;
                self.load_records(self.current_min - 1, origin="pager");
            });
        }
    },
    /**
     * Updates the pager based on the provided dataset's information
     *
     * @param {int} current_min Min pager value
     */
    update_pager: function (current_min) { 
        //console.log("MapView.update_pager");
        if (this.pager) {
            var new_state = { size: this.dataset.size(), limit: this._limit };
            if (current_min) {
                new_state.current_min = current_min;
            }
            this.pager.update_state(new_state);
        }
    },
    /**
     * No idea what this is for... apparently triggered when the web page gets refreshed?
     */
    do_load_state: function(state, warm) { 
        //console.log("MapView.do_load_state: ",state,warm);
        var reload = false;
        if (state.min && this.current_min !== state.min) {
            //this.current_min = state.min;
            reload = true;
        }
        if (state.limit) {
            if (_.isString(state.limit)) {
                state.limit = null;
            }
            if (state.limit !== this._limit) {
                this._limit = state.limit;
                reload = true;
            }
        }
        if (reload) {
            this.update_pager(state.min);
            //this.load_records(this.current_min - 1, origin="reload");
        }
    },
    do_show: function () {
        this._super();
        if (this.sidebar) {
            // Hide the sidebar by default (will be shown once a record is selected)
            this.sidebar.do_hide();
        }
    },
    /**
     * remove the map on destroy() so it doesn't generate an error when trying to load the map view of another model.
     */
    destroy: function () {
        //console.log("MapView.destroy")
        this.map.the_map.remove();
        this.map.the_map = null;
        return this._super.apply(this, arguments);
    },
    get_selected_ids: function() {
        var ids = this.map.record_displayer.get_record_ids();
        return ids;
    },
});
/**/
MapView.Map = Widget.extend({
    custom_events: {
        'map_attached': 'on_map_attached',
    },
    defaults: _.extend({},{
        center: [48.056,-2.818], // BRETAGNE
        zoom: 8,
        minZoom: 5,
        maxZoom: 18,
        tile_server_addr: TILE_SERVER_ADDR,
        container_id: 'lf_map', // the id of the container for the map
        set_bounds_mode: 'visible',
    }),
    /**
     *  Instantiate the map and attach it to its container.
     *  
     *  @param {MapView} view View 
     */
    init: function(args) {
        //console.log("MapView.Map.init args: ",args);
        this._super(args.view);
        this.options = _.defaults(args.options||{},this.defaults);
        this.view = args.view;

        this.layer_groups = []; // List of layer groups. 
        this.current_layer_group_index = 0;
        //this.controls = []; // maybe useful for more than one control
        this.ids_dict = {}; // object linking ids to _leaflet_ids

        this.the_map = null; // will be set in this.attach_to_container
        this.cmptry = 0; // used by this.attach_to_container
        this.attach_to_container(this.options.container_id,this.options.tile_server_addr);
        //console.log("MapView.Map inited: ", this);
    },
    /**
     *  Instantiate the legend displayer for the map. See map_controls.
     */
    add_legend_displayer: function () {
        //console.log("MapView.Map.add_legend_displayer");
        // make sure to only add it once.
        if (!this.legend_displayer) {
            this.legend_displayer = new map_controls.LegendDisplayer(this.view,this.options.displayer_options);
            this.legend_displayer.addTo(this.the_map);
        }else{
            console.log('this.legend_displayer is already set');
        }

        return $.when();
    },
    /**
     *  Instantiate the record displayer for the map. See map_controls.
     */
    add_record_displayer: function () {
        //console.log("MapView.Map.add_record_displayer");
        // make sure to only add it once.
        if (!this.record_displayer) {
            this.record_displayer = new map_controls.RecordDisplayer(this.view,this.options.displayer_options);
            this.record_displayer.addTo(this.the_map);
        }else{
            console.log('this.record_displayer is already set');
        }
        
        return $.when();
    },
    /**
     *  Instantiate the nocontent displayer for the map. See map_controls.
     */
    add_nocontent_displayer: function () {
        //console.log("MapView.Map.add_nocontent_displayer");
        // make sure to only add it once.
        if (!this.nocontent_displayer) {
            var options = {};

            this.nocontent_displayer = new map_controls.NoContentDisplayer(this.view,options);
            this.nocontent_displayer.addTo(this.the_map);
        }else{
            console.log('this.nocontent_displayer is already set');
        }

        return $.when();
    },
    /**
     *  @TODO: implement this. 
     *  buttons to add: 
     *      'clear selection' -> clears the current selection of records
     */
    add_buttons: function() {

    },
    /**
     *  Handler for custom event map_attached fired when the map is attached to its container.
     *  Adds controls and perfoms a search.
     */
    on_map_attached: function () {
        //console.log("MapView.Map.on_map_attached");=
        var p1 = this.add_record_displayer();
        var p2 = this.add_nocontent_displayer();
        var p3 = this.add_legend_displayer();
        //this.add_buttons(); // later, later...

        var self = this;

        $.when(p1,p2,p3).then(function(){
            var v = self.view;
            v.do_search(v.domain,v.context,v.group_by);
        });
        // when the map is loaded and attached to the container, if needed we will hide the pager above the map.
        if (self.view.hide_pager == '1') {
            self.view.ViewManager.$el.find('.o_x2m_control_panel').addClass('o_hidden');
        }
    },
    /**
     *  adds a layer group to the map's list of layer groups.
     *
     *  @param {Array} records list of records to put in the layer group.
     *  @param {Boolean} render true if we want to render the new layer_group. defaults to true.
     *  @param {Object} options A set of options used to configure the layer group.
     */
    add_layer_group: function(records, options={},render=true) {
        //console.log("MapView.Map.add_layer_group: ",arguments);
        var layer_group = new MapView.LayerGroup(this,records,options);
        this.layer_groups.push(layer_group);
        this.current_layer_group_index = this.layer_groups.length - 1;
        if (render) {
            this.render_one(layer_group);
        }
    },
    /**
     *  renders a layer group and adds it to the map
     *  
     *  @param {MapView.LayerGroup} layer_group the layer group to be rendered.
     *  @param {Boolean} set_bounds true if we want to adjust the map's bound to the newly rendered layer group. Defaults to true.
     */
    render_one: function(layer_group,set_bounds=true) {
        //console.log("MapView.Map.render_one");
        if (this.is_attached()) {
            if (!this.the_map.hasLayer(layer_group.the_layer)) {
                var self = this;
                layer_group.renderElement(true);
            }else{
                console.log("??????");
            }
            return $.when();
        }
    },

    /**
     *  Renders all layer groups and adds them to the map. Not used at the moment but should be useful on group_by implementation
     */
    render_all: function() {
        //console.log("MapView.Map.render_all");
        if (this.is_attached()) {
            for (var i=0; i<this.layer_groups.length; i++) {
                this.render_one(this.layer_groups[i],false);
            };
            return $.when().then(this.set_bounds(this.options.set_bounds_mode));
        }
    },

    /**
     *  Fits the bounds of the map according to a given mode.
     *  
     *  @param {String} mode Mode to apply. Defaults to 'visible'.
     */
    set_bounds: function (mode=this.options.set_bounds_mode) {
        //console.log("Set bounds")
        var bounds = new L.LatLngBounds();
        switch (mode) {
            case 'visible': 
                bounds.extend(this.get_visible_bounds());
                break;
            case 'current':
                var current_layer = this.layer_groups[this.current_layer_group_index];
                bounds.extend(current_layer.get_bounds());
                break;
            case 'current_visible': 
                var current_layer = this.layer_groups[this.current_layer_group_index];
                bounds.extend(current_layer.get_visible_bounds());
                break;
            case 'all':
                bounds.extend(this.get_bounds());
                break;
            default:
                console.log("given string doesn't match any of the available modes. modes are 'visible', 'current', current_visible' and 'all'");
        };
        
        if (!isNullOrUndef(bounds._northEast)) {
            this.the_map.fitBounds(bounds, {padding: [30, 30]});
        }
        if (this.the_map.getZoom() > 15) {
            this.the_map.setZoom(15);
        }
        //console.log("the_map: ",this.the_map,bounds);
        var self = this;
        //setTimeout(function(){self.the_map.invalidateSize()}, 3000)
    },

    /**
     *  Returns the bounds of all markers in all layer groups
     */
    get_bounds: function() {
        //console.log("MapView.Map.get_bounds");
        var bounds = new L.LatLngBounds();

        for (var ind=0; ind<this.layer_groups.length; ind++) {
            var layer = this.layer_groups[ind];
            bounds.extend(layer.get_bounds());
        }
        return bounds;
    },

    /**
     *  Returns the bounds of all visible markers in all visible layer groups.
     */
    get_visible_bounds: function() {
        //console.log("MapView.Map.get_visiblebounds");
        var bounds = new L.LatLngBounds();

        for (var ind in this.layer_groups) {
            var layer = this.layer_groups[ind];
            if (layer.visible) {
                bounds.extend(layer.get_visible_bounds());
            }  
        }
        return bounds;
    },

    /**
     *  Looks through the layer groups and returns the one containing the record. false if not found
     *  
     *  @param {int} id Record id.
     *  @return {MapView.LayerGroup|Boolean} l Layer group containing the record, false if not found
     */
    find_record_layer_group: function(id) {
        //console.log("MapView.Map.find_record_layer_group");
        var i=false,l=false;
        for (var j=0; j<this.layer_groups.length && i===false; j++) {
            i = this.layer_groups[j].has_record(id);
            if (i) {
                l = this.layer_groups[j];
                break;
            }
        }

        if (!l) console.log("Couln't find record id#"+id+" in current layer groups.")
        
        return l;
    },
    /**
     *  Remove all layer groups from the map, then sets this.layer_groups to [].
     */
    reset_layer_groups: function() {
        //console.log("MapView.Map.reset_layer_groups");
        if (this.is_attached()) {
            var current_layer;
            for (var i=0; i<this.layer_groups.length; i++) {
                current_layer = this.layer_groups[i].the_layer;
                if (this.the_map.hasLayer(current_layer)) {
                    this.the_map.removeLayer(current_layer);
                }else{
                    console.log("the_map doesn't have the layer...")
                }
            };
            this.layer_groups = [];
            this.record_displayer.remove_all();
            return $.when();
        };
    },
    /**
     *  Looks for the map container, then inits the map, binds its tile layer and reload content.
     *  Workaround asynchronicity.
     *
     *  @param {String} container_id Id of the container for the map.
     *  @param {String} tile_server_addr Tile server address.
     */
    attach_to_container: function (container_id,tile_server_addr) {
        //console.log("MapView.Map.attach_to_container");
        var self = this;
        if ($('#'+container_id).length > 0) {
            //console.log("this.the_map before test: ",this.the_map);

            if (this.the_map === null || this.the_map === undefined) {
                this.the_map = L.map(this.options.container_id, { 
                    center: this.options.center, 
                    zoom: this.options.zoom, 
                    minZoom: this.options.minZoom, 
                    maxZoom: this.options.maxZoom,
                });
                L.tileLayer(tile_server_addr).addTo(this.the_map);
            }else{
                console.log("the map has already been initialised");
            }
            
            return $.when().then(function(){
                //console.log('map attached!!!!!! by id. at try number '+(self.cmptry+1));
                self.trigger_up('map_attached');
                return true;
            });
        }else{
            if (this.cmptry<40) {
                this.cmptry++;
                setTimeout(function(){
                    return $.when().then(self.attach_to_container(container_id,tile_server_addr));
                },40);
            }else if (this.cmptry<100) {
                 this.cmptry++;
                 setTimeout(function(){
                     return $.when().then(self.attach_to_container(container_id,tile_server_addr));
                 },100);
             }else{
                console.log('container not found after '+this.cmptry+' try.');
                return false;
            }
        }
    },

    is_attached: function() { return this.the_map!==null && this.the_map!==undefined; },

});

MapView.LayerGroup = Widget.extend({
    defaults: _.extend({},{
        custom_icon: true,
        color_icons: true,
        // custom icon options. 
        icon_options: {
            unselected: {
                prefix: 'mdi',
                glyph: 'circle-outline',
                glyphPrefix: 'numeric',
                glyphSuffix: 'circle-outline'
            },
            selected: {
                prefix: 'mdi',
                glyph: 'circle',
                glyphPrefix: 'numeric',
                glyphSuffix: 'circle'
            }
        },
        visible: true, // false if none of the markers in this layer group is visible
        auto_addTo: true, // true to automatically add the_layer to the_map on rendering
    }),
    /**
     *  @constructs instance.of_map_view.MapView.LayerGroup
     *  @extends instance.web.Widget
     * 
     *  @param {MapView.Map} map map containing this layer group
     *  @param {Array} records records in this group
     *  @param {Object} options A set of options used to configure the layer group.
     */
    init: function(map, records, options) {
        //console.log("MapView.LayerGroup.init: ",arguments);
        this._super(map.view);
        this.records = records || [];
        this.options = _.defaults(options,this.defaults);
        this.init_icon_options();
        this.icon = null;
        this.the_layer = new L.LayerGroup();
        // the view's number of records per page (|| section), defaults to 80
        this._limit = map.view._limit;
        // the index of the first displayed record (starting from 1)
        this.current_min = 1;
        this.current_max = this.current_min + this._limit;
        //this.pages = {};

        this.visible = this.options.visible;
        if (!this.visible) this.do_toggle(false);
        
        this.map = map;
        this.current_selection = {}; // id dictionary of records currently selected. of the form id: record
        //console.log("MapView.LayerGroup this: ",this);
    },
    /**
     *  init icon options, for marker sizes
     */
    init_icon_options: function() {
        var marker_size = this.options.marker_size;
        var base_path = '/of_map_view/static/src/img/marker-icon';
        var shadow_path = '/of_map_view/static/src/img/marker-shadow';
        var marker_height = 41;
        var marker_width;
        var shadow_height = 41;
        var glyph_size = '18px';  // set to 18px for numeric mdi icons
        var glyph_anchor = [4, -7]; // left, top
        if (marker_size) {
            base_path += '-' + marker_size + '-';
            shadow_path += '-' + marker_size;
            switch (marker_size) {
                case 'x-small':
                    marker_height = 10;
                    shadow_height = 10;
                    glyph_size = '6px';
                    glyph_anchor = [0, -8];
                    break;
                case 'small':
                    marker_height = 20;
                    shadow_height = 20;
                    glyph_size = '10px';
                    glyph_anchor = [1, -3];
                    break;
            }
        }else{
            base_path += '-medium-';
            shadow_path += '-medium';
        }
        marker_width = marker_height / H2W_RATIO;
        var icon_options_dict = {
            'shadowUrl': shadow_path + '.png',
            'shadowSize': [shadow_height, shadow_height],
            'shadowAnchor': [shadow_height / 4 + 1 , shadow_height - 1],
            'iconSize': [marker_width, marker_height],
            'iconAnchor': [marker_width / 2, marker_height - 1],
            'glyphSize': glyph_size,
            'glyphAnchor': glyph_anchor
        }
        this.options.icon_options.unselected = _.extend(this.options.icon_options.unselected, icon_options_dict);
        this.options.icon_options.selected = _.extend(this.options.icon_options.selected, icon_options_dict);
        this.options.icon_options['icon_path'] = base_path;
    },
    /**
     *  looks like this one is never used? les arcanes du javascript sont souvent impénétrables!
     */
    update_records: function(new_records) {
        for (var i=0; i<this.records.length; i++) {
            if (this.records[i] == undefined && new_records[i] != undefined) {
                this.records[i] = new_records[i];
                console.log("new record in list (layergroup): IT IS USED");
            }
        }
    },
    /**
     *  renders one record
     */
    render_one_record: function(i,mode="index",visible=true) {
        //console.log("MapView.LayerGroup.render_one_record: ",this.records[i]);
        var self = this;

        if (mode == "index") {
            if (this.records[i] == undefined) {
                console.log("undefined record at index ",i);
                return;
            }
            var lat, lng, marker, icon, id, number, geojson, endpoint_geojson, manyNumbers;
            var latlngs = [];
            var geojsonLines = [];
            var endpointGeojsonLines = [];
            lat = this.records[i][this.options.latitude_field];
            lng = this.records[i][this.options.longitude_field];
            geojson = this.records[i][this.options.geojson_data];
            endpoint_geojson = this.records[i][this.options.endpoint_geojson_data] || false;
            latlngs.push([lat, lng]);
            if (geojson) {
                geojsonLines.push(JSON.parse(geojson));
            }
            if (endpoint_geojson) {
                endpointGeojsonLines.push(JSON.parse(endpoint_geojson));
            }
            number = this.records[i][this.options.number_field] || false;
            if (typeof number == "number") {
                number = number.toString();
            }
            manyNumbers = number && number.split(',').length > 1 || false;
            if (this.options.custom_icon) {
                var options = this.options.icon_options.unselected;
                options['id'] = 'icon_'+this.records[i].id;
                options['number'] = number;
                options['iconUrl'] = this.get_color_url(this.records[i]);
                options['glyphSize'] = '18px';
                if (number && !manyNumbers && parseInt(number) < 11) {
                    options['prefix'] = 'mdi';
                    options['glyph'] = options['glyphPrefix'] + '-' + number + '-' + options['glyphSuffix'];
                } else if (number && (parseInt(number) >= 11 || manyNumbers)) {
                    // If the number is greater than 10 or if there are two numbers separated by a comma,
                    // we only display strings. Because we can't display more than 1 digit as a glyph.
                    // TODO: find a way to display more than 1 digit as a glyph (maybe try to combine 2 glyphs? Or don't use glyphs at all?)
                    options['prefix'] = '';
                    if (!manyNumbers) {
                        options['glyph'] = number;
                    } else {
                        options['glyph'] = number.split(',')[0] + '...';
                        options['glyphSize'] = '14px';
                    }
                } else {
                    options['prefix'] = 'mdi';
                    options['glyph'] = 'radiobox-blank';
                }
                icon = L.icon.glyph(options);
                marker = new MapView.Marker([lat, lng],this,this.records[i],{icon:icon});
            }else{
                marker = new MapView.Marker([lat, lng],this,this.records[i]);
            }
            this.the_layer.addLayer(marker);
            marker.set_ids_dict_ref();
            this.records[i]["rendered"] = true;
        }else{
            //console.log("mode not yet implemented")
        }

        return $.when();
    },
    /**
     *  Adds markers to the layer for each record. Adds leaflet id reference in this.map.ids_dict
     */ 
    renderElement: function(set_bounds=true) {
        //console.log("MapView.LayerGroup.renderElement");
        this._super();
        var self = this;
        if (this.the_layer!==null) {
            this.the_layer.clearLayers();
        }
        this.the_layer = new L.LayerGroup();
        var lat, lng, marker, icon, id, number, geojson, endpoint_geojson, additionnalRecords, manyNumbers;
        var latlngs = [];
        var geojsonLines = [];
        var endpointGeojsonLines = [];
        for (var i=0; i<this.records.length; i++) {
            if (this.records[i] == undefined || this.records[i].rendered) {
                continue;
            }
            lat = this.records[i][this.options.latitude_field];
            lng = this.records[i][this.options.longitude_field];
            geojson = this.records[i][this.options.geojson_data];
            endpoint_geojson = this.records[i][this.options.endpoint_geojson_data] || false;
            latlngs.push([lat, lng]);
            if (geojson) {
                geojsonLines.push(JSON.parse(geojson));
            }
            if (endpoint_geojson) {
                endpointGeojsonLines.push(JSON.parse(endpoint_geojson));
            }
            number = this.records[i][this.options.number_field] || false;
            if (typeof number == "number") {
                number = number.toString();
            }
            manyNumbers = number && number.split(',').length > 1 || false;
            if (this.options.custom_icon) {
                var options = this.options.icon_options.unselected;
                options['id'] = 'icon_'+this.records[i].id;
                options['number'] = number;
                options['iconUrl'] = this.get_color_url(this.records[i]);
                options['glyphSize'] = '18px';
                if (number && !manyNumbers && parseInt(number) < 11) {
                    options['prefix'] = 'mdi';
                    options['glyph'] = options['glyphPrefix'] + '-' + number + '-' + options['glyphSuffix'];
                } else if (number && (parseInt(number) >= 11 || manyNumbers)) {
                    // If the number is greater than 10 or if there are two numbers separated by a comma,
                    // we only display strings. Because we can't display more than 1 digit as a glyph.
                    // TODO: find a way to display more than 1 digit as a glyph (maybe try to combine 2 glyphs? Or don't use glyphs at all?)
                    options['prefix'] = '';
                    
                    if (!manyNumbers) {
                        options['glyph'] = number;
                    } else {
                        options['glyph'] = number.split(',')[0] + '...';
                        options['glyphSize'] = '14px';
                    }
                } else {
                    options['prefix'] = 'mdi';
                    options['glyph'] = 'radiobox-blank';
                }
                icon = L.icon.glyph(options);
                marker = new MapView.Marker([lat, lng],this,this.records[i],{icon:icon});
            }else{
                marker = new MapView.Marker([lat, lng],this,this.records[i]);
            }
            this.the_layer.addLayer(marker);
            marker.set_ids_dict_ref();
            this.records[i]["rendered"] = true;
        }
        // Add the current marker if there is an additionnal record
        additionnalRecords = this.options.additional_records || false;
        if (additionnalRecords){
            for (var i = 0; i < this.options.additional_records.length; i++) {
                let additionnalRecord = this.options.additional_records[i]
                if (additionnalRecord.geo_lat || additionnalRecord.geo_lng){
                    var options = this.options.icon_options.unselected;
                    // this id is a negative value to avoid conflict with existing ids of real markers
                    number = additionnalRecord.number || false;
                    options['id'] = 'icon_' + additionnalRecord.id;
                    options['iconUrl'] = this.get_color_url(false, additionnalRecord.iconUrl);
                    options['prefix'] = 'mdi';
                    options['number'] = number;
                    if (number == 'start' || number == 'stop') {
                        options['glyph'] = 'home-circle-outline';
                    } else {
                        options['glyph'] = 'radiobox-blank';
                    }
                    icon = L.icon.glyph(options);
                    marker = new MapView.Marker([additionnalRecord.geo_lat, additionnalRecord.geo_lng], this, additionnalRecord, {icon:icon});
                    this.the_layer.addLayer(marker);
                    marker.set_ids_dict_ref();
                }
            }
            // if we have additionnal record we draw the route between the previous/next marker and the current fake one
            if (this.options.draw_routes == '1' && this.options.additional_record_geojson_data.length > 0) {
                this.do_draw_routes_addtionnal_record(this.options.additional_record_geojson_data);
            }
        }
        if (this.options.auto_addTo) {
            this.the_layer.addTo(this.map.the_map);
            this.visible = true;
            if (this.options.connect_markers == '1' && latlngs.length > 0) {
                this.do_connect_dot(latlngs);  // Add simple lines between the markers on the map
            }
            if (this.options.draw_routes == '1') {
                // Draw routes get by the geojson data for the endpoint
                this.do_draw_routes_from_records();
            }
            this.do_show_range(this.map.view.current_min-1,false,true,set_bounds);
        }

        return $.when(); 
    },
    /**
     *  returns the URL for the icon, given the color_field. defaults to blue.
     */
    get_color_url: function (record, color='blue') {
        var color_field =  this.options.color_field;
        var base_path = this.options.icon_options.icon_path;
        if (record && color_field && record[color_field] && record[color_field] == 'grey') {
            return base_path + 'gray.png';
        }else if (record && color_field && record[color_field]) {
            return base_path + record[color_field] + '.png';
        }else{
            return base_path + color + '.png';
        }
    },
    /**
     *  Gets the bounds of all markers in this layer group
     *
     *  @return {L.LatLngBounds} bounds bounds of all markers in this layer group
     */
    get_bounds: function () {
        //console.log("MapView.LayerGroup.get_bounds");
        var bounds = new L.LatLngBounds();
        var zerozero = [0,0];
        var marker_latlng;

        for (var id in this.the_layer._layers) {
            var marker = this.the_layer._layers[id];
            marker_latlng = [marker._latlng["lat"],marker._latlng["lng"]];
            if (JSON.stringify(marker_latlng) != JSON.stringify(zerozero)) {
                bounds = bounds.extend(marker.getBounds ? marker.getBounds() : marker.getLatLng());
            }
            bounds.extend(marker.getBounds ? marker.getBounds() : marker.getLatLng());
        }
        return bounds;
    },
    /**
     *  Same as get_bounds, but only for visible markers
     *
     *  @return {L.LatLngBounds} bounds bounds of all visible markers in this layer group
     */
    get_visible_bounds: function () {
        //console.log("MapView.LayerGroup.get_visible_bounds");
        var bounds = new L.LatLngBounds();
        var zerozero = [0,0];
        var marker_latlng;
        //console.log("this.the_layer._layers: ",this.the_layer._layers);

        for (var id in this.the_layer._layers) {
            var marker = this.the_layer._layers[id];

            marker_latlng = [marker._latlng["lat"],marker._latlng["lng"]];
            //console.log("marker_latlng: ",marker_latlng);
            if (marker.visible && JSON.stringify(marker_latlng) != JSON.stringify(zerozero)) {
                bounds = bounds.extend(marker.getBounds ? marker.getBounds() : marker.getLatLng());
            }else if (JSON.stringify(marker_latlng) == JSON.stringify(zerozero)) {
                //console.log("zerozero marker");
            }else{
                //console.log("invisible marker");
            }
        }
        //console.log("BOUNDS: ",bounds);
        return bounds;
    },

    /**
     *  Looks for a record by id
     *  
     *  @param {int} id id of the record
     *  @return {Boolean} found true if the record was found
     */
    has_record: function (id) {
        //console.log("MapView.LayerGroup.has_record");
        var found = false;
        for (var i=0; i<this.records.length && found === false; i++) {
            if (this.records[i] != undefined && this.records[i].id === id) { // record found
                found = true;
                break;
            }
        }
        // If there are fake markers, we need to check them too
        for (var i=0; i<this.options.additional_records.length && found === false; i++) {
            if (this.options.additional_records[i] != undefined && this.options.additional_records[i].id === id) {
                found = true;
                break;
            }
        }
        return found;
    },
    /**
     *  Updates the current selection of records.
     *
     *  @param {String} mode update mode. 'add' or 'remove'.
     *  @param {Object} record record to add or remove from the selection. 
     */
    update_selection: function(mode,record) { //called by this.map.record_displayer
        //console.log("MapView.LayerGroup.update_selection");
        var updated = false;
        switch (mode) {
            case 'add': 
                this.current_selection[record.id] = record;
                updated = true;
                break;
            case 'remove':
                delete this.current_selection[record.id];
                updated = true;
                break;
            default: console.log('MapView.LayerGroup.update_selection incorrect mode');
        }
        //if (updated) console.log('MapView.LayerGroup.update_selection: ',this.current_selection);
    },
    /**
     *  Clears the current selection of records. Called by the record displayer
     */
    clear_current_selection: function() {
        //console.log("MapView.LayerGroup.clear_current_selection");
        for (var k in this.current_selection) {
            var marker = this.the_layer._layers[this.map.ids_dict[k]];
            if (marker.selected) {
                marker.do_toggle_selected(false);
            }
        }
        this.current_selection = {};
    },
    /**
     *  Displays (make visible) all markers in range [ i1,i2 [, calls this.render_one_record to render markers not yet rendered.
     *
     *  @param {Int} i1 Start index of the range, included in the range.
     *  @param {Int} i2 End index of the range, not included in the range.
     *  @param {Boolean} hide_rest True to hide the rest of the markers, ie to only show the given range. Defaults to false
     */
    do_show_range: function (i1,i2,hide_rest=false,set_bounds=true) {
        //console.log("MapView.LayerGroup.do_show_range: ",i1,i2,hide_rest,set_bounds);
        if (!i2){ // full page
            i2 = i1 + this._limit;
        }
        if (i2 > this.records.length) { // foolproofing
            i2 = this.records.length;
        }
        if (i1 < 0) { // foolproofing
            i1 = 0;
        }
        var lf_id;
        //console.log(this.map.ids_dict);
        for (var i=i1; i<i2; i++) {
            if (this.records[i] == undefined) {
                console.log("undefined record");
                continue;
            }
            if (!this.records[i].rendered) {
                this.render_one_record(i,"index",true);
            }
            lf_id = this.map.ids_dict[this.records[i].id];
            this.the_layer._layers[lf_id].do_toggle(true);
        }

        if (hide_rest) {
            this.do_hide_range(0,i1);
            this.do_hide_range(i2,this.records.length);
        }
        if (set_bounds) this.map.set_bounds('current_visible');
    },
    /**
     *  Hides all markers in range [ i1, i2 [ 
     *
     *  @param {Int} i1 Start index of the range, included in the range.
     *  @param {Int} i2 End index of the range, not included in the range.
     *  @param {Boolean} show_rest True to show the rest of the markers, ie to only hide the given range. Defaults to false
     */
    do_hide_range: function (i1,i2,show_rest=false) {
        //console.log("MapView.LayerGroup.do_hide_range",i1,i2,show_rest);
        if (i2 != 0 && !i2){ // full page
            i2 = i1 + this._limit;
        }
        if (i2 > this.records.length) { // foolproofing
            i2 = this.records.length;
        }
        if (i1 < 0) { // foolproofing
            i1 = 0;
        }
        for (var i=i1; i<i2; i++) {
            if (!!this.records[i] && this.records[i].rendered) {
                this.the_layer._layers[ this.map.ids_dict[this.records[i].id] ].do_toggle(false);
            }
        }
        if (show_rest) {
            this.do_show_range(0,i1);
            this.do_show_range(i2,this.records.length);
        }
    },
    do_connect_dot: function (latlngs) {
        L.polyline(latlngs, {color: DEFAULT_POLYLINE_COLOR}).addTo(this.map.the_map);
    },
    do_draw_routes_from_list: function (geojsonLines, endpoint = false) {
        // Draw route between markers on the map from a list of geojson lines, can be used to draw a route between markers from a list of geojson lines
        var self = this;
        let listAvailableColors = ROUTE_AVAILABLE_COLORS;
        var lastColor = false;
        geojsonLines.forEach(function(geoline, index) {
            let color;
            if (!endpoint && index > 0) {
                // If the route is not the startpoint/endpoint, we draw it with a different color
                color = listAvailableColors[index % listAvailableColors.length];
                while (color == lastColor) {
                    color = listAvailableColors[Math.floor(Math.random() * listAvailableColors.length)];
                }
                lastColor = color;
            } else {
                color = DEFAULT_TOUR_START_STOP_COLOR;
            }
            L.geoJSON(geoline, {'color': color}).addTo(self.map.the_map);
        });
    },
    do_draw_routes_addtionnal_record: function (geojsonLines) {
        var self = this;
        geojsonLines.forEach(function(geoline) {
            L.geoJSON(geoline, {'color': DEFAULT_ADDITIONNAL_RECORD_COLOR}).addTo(self.map.the_map);
        });
    },
    do_draw_routes_from_records: function () {
        // Draw route between markers on the map from records in the layer
        var self = this;
        //TODO : we can do better with layergroup!!
        //We track only lines using path , to avoid deleting the other components
        if (this.options.remove_routes == '1') {
            $('path.leaflet-interactive').remove()
        }
        for (var i = 0; i < self.records.length; i++) {
            if (self.records[i].geojson_data) {
                let geoline = JSON.parse(self.records[i].geojson_data);
                let color;
                if (i > 0) {
                    // If the route is not the startpoint/endpoint, we draw it with a different color
                    color = self.records[i].hexa_color;
                } else {
                    color = DEFAULT_TOUR_START_STOP_COLOR;
                }
                L.geoJSON(geoline, {'color': color}).addTo(self.map.the_map);

            }
            if (self.records[i].endpoint_geojson_data) {
                L.geoJSON(JSON.parse(self.records[i].endpoint_geojson_data), {'color': DEFAULT_TOUR_START_STOP_COLOR}).addTo(self.map.the_map);
            }
        }
    },
    /**
     *  Override method from Widget.
     *  Displays (make visible) all the markers
     */
    do_show: function () {
        //console.log("MapView.LayerGroup.do_show");
        var dict = this.the_layer._layers;
        for (var key in dict) {
            if (dict[key].visible) {
                console.log('this marker is already visible');
            }else{
                dict[key].do_show();
            }
        }
        this.visible = true;
    },
    /**
     *  Override method from Widget.
     *  Hides all the markers.
     */
    do_hide: function () {
        //console.log("MapView.LayerGroup.do_hide");
        var dict = this.the_layer._layers;
        for (var key in dict) {
            if (dict[key].visible) {
                dict[key].do_hide();
            }else{
                console.log('this marker is already invisible');                
            }
        }
        this.visible = false;
    },
    /**
     *  Override method from Widget.
     *  Displays (make visible) or hides all the markers
     *
     *  @param {Boolean} [display] Use true to show the widget or false to hide it
     */
    do_toggle: function (display) {
        //console.log("MapView.LayerGroup.do_toggle");
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            this.visible ? this.do_hide() : this.do_show();
        }
    },

});/**/

MapView.Marker = L.Marker.extend({
    /**
     *  @extends L.Marker
     *
     *  @param {Array} latlng Coordinates of the marker. of the form [lat,lng].
     *  @param {MapView.LayerGroup} group Layer group containing this marker.
     *  @param {Object} record Record associated to this marker.
     *  @param {Object} options A set of options used to configure the marker.
     */
    initialize: function (latlng, group, record, options) {
        //console.log("MapView.Marker.init")
        L.setOptions(this, options);
        var self = this;
        this._latlng = L.latLng(latlng);
        this.id = record.id;
        this.group = group;
        this.fields = this.group.map.view.fields;
        this.record = this.transform_record(record);
        //console.log("RECORD: ",this.record);
        
        // true if the marker is currently visible on the map, ie if it's on the current pager's selection
        this.visible = true;
        // true if the marker is selected. toggles from selected to unselected on click
        this.selected = false;
        // true if the marker is highlighted, ie it's selected and the mouse is over it
        this.highlighted = false;
        // for QWeb
        this.qweb = this.group.map.view.qweb;
        if (this.qweb.templates["of_map_marker_tooltip"]) {  // in case the template is not defined
            this.many2manys = this.group.map.view.many2manys;
            this.m2m_context = this.group.map.view.m2m_context;
            this.qweb_context = {
                record: this.record,
                //widget: this,
                read_only_mode: this.read_only_mode,
                user_context: session.user_context,
                formats: formats,
            };
            this.tooltip = this.qweb.render("of_map_marker_tooltip", this.qweb_context) || null;
        }
        this.on('dblclick',this.open_record);
        this.on('click',this.do_toggle_selected);
        this.on('mouseover',this.do_toggle_highlighted);
        this.on('mouseout',this.do_toggle_highlighted);
        this.on("add",this.bind_tooltip);
    },
    /**
     *  binds tooltip to the marker if any
     */
    bind_tooltip: function() {
        var $el = $("#glyph_icon_" + this.id).parent();
        if ($el.length && this.tooltip) {
            $el.tooltip({
                'html': true,
                'title': this.tooltip,
                'delay': {'show': 50}
            })
        }else{
            //console.log("TODAVIA NO");
        }
    },
    /**
     *  transforms the record so it can be used by QWeb renderer
     */
    transform_record: function(record) {
        var self = this;
        var new_record = {};
        _.each(_.extend(_.object(_.keys(this.fields), []), record), function(value, name) {
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
     *  Adds a reference to the map's ids_dict: this.id -> this._leaflet_id. Called when the marker is added to its layer group
     */
    set_ids_dict_ref: function() {
        //console.log("MapView.Marker.set_ids_dict_ref");
        this.group.map.ids_dict[this.id] = this._leaflet_id;
    },
    /**
     *  Opens the form view of the record
     */
    open_record: function() {
        //console.log("MapView.Marker.open_record");
        this.group.trigger_up('map_record_open', {id: this.id});
        return $.when();
    },
    /**
     *  Selects or unselects the marker. Will toggle if no parameter given.
     *
     *  @param {Boolean} [display] use true to select the marker or false to unselect it
     */
    do_toggle_selected: function(select) {
        //console.log("MapView.Marker.do_toggle_selected");
        var changed = false
        if (_.isBoolean(select)) {
            if (!this.selected === select){
                changed = true;
            }
            this.selected = select;
        } else {
            this.selected = !this.selected;
            changed = true;
        }
        //console.log('MapView.Marker id#'+this.id+' selected: '+this.selected);
        if (changed) {
            if (this.selected) {
                //console.log('marker selected: ',this);
                this.group.map.record_displayer.add_record(this,this.group.map.view.record_options);
                if (this.group.map.view.sidebar) {
                    this.group.map.view.sidebar.do_show();
                }
            }else{
                this.group.map.record_displayer.remove_record(this.id);
                if (this.group.map.record_displayer.get_record_ids().length == 0) {
                    if (this.group.map.view.sidebar) {
                        this.group.map.view.sidebar.do_hide();
                    }
                }
            }
            this.do_toggle_highlighted(); // workaround. without it the marker would be highlighted on mouseout
            this.update_glyph();
        }
    },
    /**
     *  Highlights or downplays the marker through the record displayer.
     */
    do_toggle_highlighted: function() {
        //console.log("MapView.Marker.do_toggle_highlighted");
        if (this.selected) {
            this.highlighted = !this.highlighted;
            this.group.map.record_displayer.do_highlight_record(this.id,this.highlighted);
        }else if (this.highlighted) {
            //console.log('highlighted marker: ',this.highlighted);
            this.highlighted = !this.highlighted;
            this.group.map.record_displayer.do_highlight_record(this.id,this.highlighted,true); // we need to force because the record is not in the record displayer list of records
        }
    },
    /**
     *  Updates the icon's glyph. Called when a marker is selected or unselected, ie by click on its icon
     */
    update_glyph: function() {
        var withPrefix = this.options.icon && this.options.icon.options['prefix'] !== '';
        // We only change the glyph if the icon has a prefix, some records have no prefix and are only the number of the element instead of a glyph
        if (withPrefix) {
            var glyph_id = '#glyph_icon_'+this.id;
            var selected_glyph_class, unselected_glyph_class;
            if (this.options.icon.options['glyph'] == 'radiobox-blank' || this.options.icon.options['number'] == false) {
                selected_glyph_class = this.group.options.icon_options.selected.prefix + "-" + this.group.options.icon_options.selected.glyph;
                unselected_glyph_class = this.group.options.icon_options.unselected.prefix + "-" + this.group.options.icon_options.unselected.glyph;
            } else {  // MDI numeric icon selectors
                if (this.options.icon.options['number'] == 'start' || this.options.icon.options['number'] == 'stop') {
                    selected_glyph_class = this.group.options.icon_options.selected.prefix + '-home-circle';
                    unselected_glyph_class = this.group.options.icon_options.unselected.prefix + '-home-circle-outline';
                } else {
                    selected_glyph_class = `${this.options.icon.options['prefix']}-${this.group.options.icon_options.selected.glyphPrefix}-${this.options.icon.options['number']}-${this.group.options.icon_options.selected.glyphSuffix}`;
                    unselected_glyph_class = `${this.options.icon.options['prefix']}-${this.group.options.icon_options.unselected.glyphPrefix}-${this.options.icon.options['number']}-${this.group.options.icon_options.unselected.glyphSuffix}`;
                }
            }
            var $glyph = $(glyph_id);
            if ($glyph.length>0) {
                if ($glyph.hasClass(selected_glyph_class)) {
                    $glyph.removeClass(selected_glyph_class);
                    $glyph.addClass(unselected_glyph_class);
                }else{
                    $glyph.removeClass(unselected_glyph_class);
                    $glyph.addClass(selected_glyph_class);
                }
            }else{
                console.log("update_glyph: couldn't find glyph id"+glyph_id);
            }
        }
    },
    /**
     *  Updates the marker color. Called when a map_record is updated
     */
    update_color: function (color) {
        //console.log("Update color: ",this);
        var options;
        this.selected ? options = this.group.options.icon_options.selected : options = this.group.options.icon_options.unselected;
        options['id'] = 'icon_'+this.id;
        color = color || 'blue';
        options['iconUrl'] = this.group.options.icon_options.icon_path + color + '.png';

        var icon = L.icon.glyph(options);
        this.setIcon(icon);
    },
    /**
     *  returns the URL for the icon. defaults to blue.
     */
    get_color_url: function (record, color='blue') {
        return this.group.get_color_url(record, color);
    },
    /**
     *  Displays (make visible) the marker
     */
    do_show: function () {
        //console.log("MapView.Marker.do_show");
        L.DomUtil.removeClass(this._icon,'o_hidden');
        L.DomUtil.removeClass(this._shadow,'o_hidden');
        this.visible = true;
    },
    /**
     *  Hides the marker
     */
    do_hide: function () {
        //console.log("MapView.Marker.do_hide");
        L.DomUtil.addClass(this._icon,'o_hidden');
        L.DomUtil.addClass(this._shadow,'o_hidden');
        this.visible = false;
    },
    /**
     *  Displays (make visible) or hides the marker
     *
     *  @param {Boolean} [display] use true to show the marker or false to hide it
     */
    do_toggle: function (display) {
        //console.log("MapView.Marker.do_toggle: ",display);
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            L.DomUtil.hasClass(this._icon,'o_hidden') ? this.do_show() : this.do_hide();
        }
    },/**/

});

    core.view_registry.add('map', MapView);

    return MapView;
})
