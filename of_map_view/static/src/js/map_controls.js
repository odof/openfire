odoo.define('of_map_view.map_controls', function (require) {
"use strict";

var MapRecord = require('of_map_view.map_record');

L.Control.RecordDisplayer = L.Control.extend({
	options: {
		position: 'topleft'
  	},
  	/**
	 *	Inits the displayer.
	 */
  	initialize: function(view,header_fields,body_fields,options) {
  		//console.log('RecordDisplayer.initialize');
  		//console.log('RecordDisplayer: ',this);
  		L.Util.setOptions(this, options);
  		this.header_content = '';
  		this.body_content = '';
  		this.header_fields = header_fields;
		this.body_fields = body_fields;
		this.view = view;
		this.map = this.view.map;
		this.records = {};
 	},
 	/**
	 *  Renders the displayer.
	 */
 	onAdd: function(map) {
 		//console.log('RecordDisplayer.onAdd');
  		var container_tag = 'div';
  		var container_class = 'o_record_display_control';
  		this.container = L.DomUtil.create(container_tag, container_class);
  		this.container.style.backgroundColor = 'transparent';

		return this.container;
	},
	/**
	 *
	 */
	onRemove: function(map) {
  		// Tear down the control.
	},
	/**
	 *	Adds a record to the displayer.
	 *
	 *	@param {Object} record Record to add.
	 *	@param {Object} options A set of options used to configure the map_record.
	 */
	add_record: function(record,options) {
		//console.log('RecordDisplayer.add_record: ',record,options);
		var map_record = new MapRecord(this.view,record,this,options);
		this.records[record.id] = map_record;
		map_record.render();

		var layer_group = this.map.layer_groups[this.map.current_layer_group_index];
		layer_group.update_selection('add',record);

		//console.log('RecordDisplayer.records: ',this.records);
	},
	/**
	 *  Remove all records from the displayer.
	 */
	remove_all: function() {
		//console.log("RecordDisplayer.remove_all");
		var layer_group = this.map.layer_groups[this.map.current_layer_group_index];
		if (layer_group) {
			layer_group.clear_current_selection();
		}
		for (var k in this.records) {
			this.records[k].destroy();
			delete this.records[k];
		}
		this.records = [];
		$('.record_display_control').empty();
	},
	/**
	 *	Removes a record from the displayer and updates its layer group current selection
	 *
	 *	@param {int} id id of the record to remove.
	 */
	remove_record: function(id) {
		//console.log("RecordDisplayer.remove_record");
		if (this.records[id]) {
			var layer_group = this.map.layer_groups[this.map.current_layer_group_index];
			layer_group.update_selection('remove',this.records[id]);

			this.records[id].destroy();
			delete this.records[id];
			var str = '#map_record_'+id;
			//console.log('str: ',str);
			$(str).remove();
		}else{
			throw new Error(_.str.sprintf( _t("couldn't find record id#"+id)))
		}
	},
	/**
	 *  Handles signal to highlight or downplay a record marker and map_record
	 *	
	 *	@param {int} id of the record to highlight
	 *	@param {Boolean} on true to highlight, false to downplay
	 *	@param {Boolean} force true to force the code to be executed even if the record is not selected. Workaround issue of unselected-yet-highlighted records. defaults to false.
	 */
	do_highlight_record: function (id,on,force=false) {
		//console.log("RecordDisplayer.do_highlight_record");
		if (this.records[id] || force) { // equivalent to marker selected
			var glyph_icon_id = '#glyph_icon_'+id;
			var map_record_id = '#map_record_'+id;
			var $glyph = $(glyph_icon_id);
			var $map_record = $(map_record_id);

			//console.log('$glyph: ',$glyph);
			//console.log('$map_record: ',$map_record);

			var icon_found = $glyph.length > 0;
			var record_found = $map_record.length > 0;
            if (icon_found && record_found) {
                //console.log('found glyph by id! id#'+glyph_icon_id);
                if (on) {
                	var layer = this.map.find_record_layer_group(id);
                	//console.log('LAYER: ',layer);
                	if (layer) {
                		var marker = layer.the_layer._layers[ this.map.ids_dict[id] ];
                	}
                	
                	if (!marker.visible) { // the marker is not visible
                		$glyph.css('color','lightGrey');
                    	$map_record.css('background-color','lightGrey');
                	}else{
                		$glyph.css('color','yellow');
                    	$map_record.css('background-color','yellow');
                	}
                }else{
                    $glyph.css('color','white');
                    $map_record.css('background-color','white');
                }
            }else if (icon_found) { // when a record is getting unselected for example
            	//console.log('found glyph by id! id#'+glyph_icon_id);
            	if (on) {
                    $glyph.css('color','yellow');
                }else{
                    $glyph.css('color','white');
                }
            }else{
            	if (!icon_found) console.log('could not find glyph by id! id'+glyph_icon_id);
                if (!record_found) console.log('could not find map_record by id! id'+map_record_id);
            }
		}else{
			console.log("couldn't find record id#"+id);
		}
	},
});

L.control.displayer = function(view,header_fields,body_fields,options) {
	return new L.Control.RecordDisplayer(view,header_fields,body_fields,options);
};

// not implemented yet
L.Control.TopRightButtons = L.Control.extend({

	options: {
		position: 'topleft'
  	},

  	initialize: function (options) {
    	// constructor
    	console.log('TopRightButtons: initialize');
  		console.log('TopRightButtons: ',this);
  		L.Util.setOptions(this, options);
  	},

  	onAdd: function (map) {
  		//this.container = L.DomUtil.create('input',container_class);
    	//this.container.type="button";
    	// happens after added to map
  	},

  	onRemove: function (map) {
    	// when removed
  	}

});

return {
    RecordDisplayer: L.Control.RecordDisplayer,
};

});