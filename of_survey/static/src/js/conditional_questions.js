/** @odoo-module */
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { Component, onWillStart,  useState, reactive} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

class ConditionalQuestions extends Component {
    static template = "of_survey.ConditionalQuestions";
    static props = {
        ...standardFieldProps,
    }
    static supportedTypes = ['one2many'];
    static fieldsToFetch = {
        operator : { type: "selection" },
        question_id : { type : "many2one" },
        answer_ids : { type : "many2many" },
        triggering_question_id : { type : "many2one" },
    }

    setup(){
        this.state = useState({
            suggested_answers : {}
        })

        this.orm = useService("orm");

        this.survey_id = this.props.record.model.root.data.id;

        onWillStart( async () => {
            var self = this;

            let all_questions = await self.orm.searchRead("of.survey.question", [['survey_id','=',this.survey_id]],['id','display_name','suggested_answer_ids']);
            this.suggested_answers = {};
            all_questions.map((question) => {
                this.suggested_answers[question.id] = question.suggested_answer_ids;
            })

            let all_answers = await self.orm.searchRead("of.survey.question.answer", [['question_id.survey_id','=',this.survey_id]],["id", "display_name"]);
            this.all_answers = {};
            all_answers.map((answer) => {
                this.all_answers[answer.id] = answer.display_name;
            })
        })
    }

    get conditionals(){
        return this.props.value.records;
    }

    get operators(){
        return ["AND","OR"];
    }

    get questions(){
        return this.props.record.model.root.data.question_and_page_ids.records.filter((record) => !record.data.is_page && ['simple_choice','multiple_choice'].includes(record.data.question_type) );
    }

    async AddCondition(evt){
        let newRecord = await this.props.value.addNew({
            position : "bottom",
        });
    }

    async DeleteCondition(evt,conditional){
        await this.props.value.delete(conditional.id);
    }

    async onChangeQuestion(evt,conditional){
        // on supprime les réponses déjà saisies
        conditional.data.answer_ids.records.map((record) => {
            conditional.data.answer_ids.delete(record.id);
        })
        // on met à jour la question trigger
        await conditional.update({
                'triggering_question_id' : [parseInt(evt.target.value)],
        })
        await conditional.model.notify();
    }

    async onChangeAnswer(evt,conditional){
        await conditional.data.answer_ids.add([parseInt(evt.target.value)],{ isM2M: true });
        await conditional.model.notify();
    }

    async onDeleteAnswer(evt,answer,conditional){
        await conditional.data.answer_ids.delete(answer.id);
        await conditional.model.notify();
    }

    async onChangeOperator(evt,conditional){
        await conditional.update({
                'operator' : evt.target.value,
        })
        await conditional.model.notify();
    }

}

registry.category("fields").add("conditional_questions", ConditionalQuestions);
