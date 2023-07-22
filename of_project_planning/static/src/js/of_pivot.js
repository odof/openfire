odoo.define('of_project_planning.of_pivot', function(require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var formats = require('web.formats');
var _t = core._t;

var PivotView = require('web.PivotView');

PivotView.include({
    // Redéfinition de la fonction standard afin d'appliquer des styles sur certains indicateurs de vues pivots
    draw_rows: function ($tbody, rows) {
        var self = this,
            i, j, value, $row, $cell, $header,
            nbr_measures = this.active_measures.length,
            length = rows[0].values.length,
            display_total = this.main_col.width > 1;

        var groupby_labels = _.map(this.main_row.groupbys, function (gb) {
            return self.fields[gb.split(':')[0]].string;
        });
        var measure_types = this.active_measures.map(function (name) {
            return self.measures[name].type;
        });
        var widgets = this.widgets;
        for (i = 0; i < rows.length; i++) {
            $row = $('<tr>');
            $header = $('<td>')
                .text(rows[i].title)
                .data('id', rows[i].id)
                .css('padding-left', (5 + rows[i].indent * 30) + 'px')
                .addClass(rows[i].expanded ? 'o_pivot_header_cell_opened' : 'o_pivot_header_cell_closed');
            if (rows[i].indent > 0) $header.attr('title', groupby_labels[rows[i].indent - 1]);
            $header.appendTo($row);
            for (j = 0; j < length; j++) {
                var widget = "";
                var row_value = rows[i].values[j];
                value = formats.format_value(row_value, {type: measure_types[j % nbr_measures], widget: widget});
                $cell = $('<td>')
                            .data('id', rows[i].id)
                            .data('col_id', rows[i].col_ids[Math.floor(j / nbr_measures)])
                            .toggleClass('o_empty', !value)
                            .text(value)
                            .addClass('o_pivot_cell_value text-right');
                if (((j >= length - this.active_measures.length) && display_total) || i === 0){
                    $cell.css('font-weight', 'bold');
                }
                if (this.model == 'of.periode.planifiee.technicien' && this.active_measures[j % nbr_measures] == 'occupation_rate') {
                    if (row_value !== undefined) {
                        if (row_value < 50.0) {
                            $cell.css('color', 'red');
                        }
                        else if (row_value >= 90.0 && row_value <= 100.0) {
                            $cell.css('color', 'green');
                        }
                        else if (row_value > 100.0) {
                            $cell.css('color', 'orange');
                        }
                    }
                }
                if (this.model == 'of.project.task.planning' && this.active_measures[j % nbr_measures] == 'occupation_rate') {
                    if (row_value !== undefined) {
                        if (row_value < 50.0) {
                            $cell.css('color', 'red');
                        }
                        else if (row_value >= 90.0 && row_value <= 100.0) {
                            $cell.css('color', 'green');
                        }
                        else if (row_value > 100.0) {
                            $cell.css('color', 'orange');
                        }
                    }
                }
                if (this.model == 'project.task' && this.active_measures[j % nbr_measures] == 'of_progress_rate') {
                    if (row_value !== undefined) {
                        if (row_value < 50.0) {
                            $cell.css('color', 'red');
                        }
                        else if (row_value >= 90.0) {
                            $cell.css('color', 'green');
                        }
                    }
                }
                $row.append($cell);

                $cell.toggleClass('hidden-xs', j < length - this.active_measures.length);
            }
            $tbody.append($row);
        }
    },
});
})
