odoo.define('of_survey.result', function (require) {
'use strict';

var _t = require('web.core')._t;
const { loadJS } = require('@web/core/assets');
var publicWidget = require('web.public.widget');

// The given colors are the same as those used by D3
var D3_COLORS = ["#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
                    "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
                    "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"];

// TODO awa: this widget loads all records and only hides some based on page
// -> this is ugly / not efficient, needs to be refactored
publicWidget.registry.OFSurveyResultPagination = publicWidget.Widget.extend({
    events: {
        'click li.o_survey_js_results_pagination a': '_onPageClick',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {$.Element} params.questionsEl The element containing the actual questions
     *   to be able to hide / show them based on the page number
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.$questionsEl = params.questionsEl;
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.limit = self.$el.data("record_limit");
        });
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPageClick: function (ev) {
        ev.preventDefault();
        this.$('li.o_survey_js_results_pagination').removeClass('active');

        var $target = $(ev.currentTarget);
        $target.closest('li').addClass('active');
        this.$questionsEl.find('tbody tr').addClass('d-none');

        var num = $target.text();
        var min = (this.limit * (num-1))-1;
        if (min === -1){
            this.$questionsEl.find('tbody tr:lt('+ this.limit * num +')')
                .removeClass('d-none');
        } else {
            this.$questionsEl.find('tbody tr:lt('+ this.limit * num +'):gt(' + min + ')')
                .removeClass('d-none');
        }

    },
});

/**
 * Widget responsible for the initialization and the drawing of the various charts.
 *
 */
publicWidget.registry.OFSurveyResultChart = publicWidget.Widget.extend({
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],

    /**
     * Adds a unicode 'check' mark if the answer's text is among the question's right answers.
     * @private
     * @param  {Object} value
     * @param  {String} value.text The original text of the answer
     */
    _markIfCorrect: function (value) {
        return `${value.text}${this.rightAnswers.indexOf(value.text) >= 0 ? " \u2713": ''}`;
    },

});

publicWidget.registry.OFSurveyResultWidget = publicWidget.Widget.extend({
    selector: '.o_survey_result',
    events: {
        'click .o_survey_results_topbar_clear_filters': '_onClearFiltersClick',
        'click i.filter-add-answer': '_onFilterAddAnswerClick',
        'click i.filter-remove-answer': '_onFilterRemoveAnswerClick',
        'click a.filter-finished-or-not': '_onFilterFinishedOrNotClick',
        'click a.filter-finished': '_onFilterFinishedClick',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    willStart: function () {
        var url = '/web/webclient/locale/' + (document.documentElement.getAttribute('lang') || 'en_US').replace('-', '_');
        var localeReady = loadJS(url);
        return Promise.all([this._super.apply(this, arguments), localeReady]);
    },

    /**
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var allPromises = [];

            self.$('.pagination').each(function (){
                var questionId = $(this).data("question_id");
                allPromises.push(new publicWidget.registry.SurveyResultPagination(self, {
                    'questionsEl': self.$('#survey_table_question_'+ questionId)
                }).attachTo($(this)));
            });
            if (allPromises.length !== 0) {
                return Promise.all(allPromises);
            } else {
                return Promise.resolve();
            }
        });
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

     /**
     * Add an answer filter by updating the URL and redirecting.
     * @private
     * @param {Event} ev
     */
    _onFilterAddAnswerClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.set('filters', this._prepareAnswersFilters(params.get('filters'), 'add', ev));
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * Remove an answer filter by updating the URL and redirecting.
     * @private
     * @param {Event} ev
     */
    _onFilterRemoveAnswerClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        let filters = this._prepareAnswersFilters(params.get('filters'), 'remove', ev);
        if (filters) {
            params.set('filters', filters);
        } else {
            params.delete('filters')
        }
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClearFiltersClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.delete('filters');
        params.delete('finished');
        params.delete('failed');
        params.delete('passed');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterFinishedOrNotClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.delete('finished');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterFinishedClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.set('finished', 'true');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
   
    /**
     * @private
     * @param {Event} ev
     */

    /**
     * @private
     * @param {Event} ev
     */
   

    /**
     * Returns the modified pathname string for filters after adding or removing an
     * answer filter (from click event). Filters are formatted as `"rowX,ansX", where
     * the row is used for matrix-type questions and set to 0 otherwise.
     * @private
     * @param {String} filters Existing answer filters, formatted as `rowX,ansX|rowY,ansY...`.
     * @param {"add" | "remove"} operation Whether to add or remove the filter.
     * @param {Event} ev Event defining the filter.
     * @returns {String} Updated filters.
     */
    _prepareAnswersFilters(filters, operation, ev) {
        const cell = $(ev.target);
        const eventFilter = `${cell.data('rowId') || 0},${cell.data('answerId')}`;

        if (operation === 'add') {
            filters = filters ? filters + `|${eventFilter}` : eventFilter;
        } else if (operation === 'remove') {
            filters = filters
                .split("|")
                .filter(filterItem => filterItem !== eventFilter)
                .join("|");
        } else {
            throw new Error('`operation` parameter for `_prepareAnswersFilters` must be either "add" or "remove".')
        }
        return filters;
    }
});

return {
    OFresultWidget: publicWidget.registry.OFSurveyResultWidget,
    OFchartWidget: publicWidget.registry.OFSurveyResultChart,
    OFpaginationWidget: publicWidget.registry.OFSurveyResultPagination
};

});
