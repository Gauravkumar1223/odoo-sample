/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import {registry} from '@web/core/registry';
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete, useOpenMany2XRecord, useSelectCreate } from "@web/views/fields/relational_utils";

import { Component, onWillStart, onMounted, onWillUpdateProps, useExternalListener, useRef, useState } from "@odoo/owl";

export class Many2OneImageField extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");

        const { activeActions, resModel, update, isToMany, fieldString } = this.props;

        this.openMany2X = useOpenMany2XRecord({
            resModel,
            activeActions,
            isToMany,
            onRecordSaved: (record) => {
                return update([record.data]);
            },
            onRecordDiscarded: () => {
                if (!isToMany) {
                    this.props.update(false);
                }
            },
            fieldString,
        });

        onWillStart(async () => {
            this.props.sources = await this.loadOptionsSource("");
        });

        onMounted(() => {
            //console.log('Mounted', this.props);
        });

        onWillUpdateProps(async (nextProps) => {
            nextProps.sources = await this.loadOptionsSource("");
        });
    }

    get context() {
        return this.props.record.getFieldContext(this.props.name);
    }

    get domain() {
        return this.props.record.getFieldDomain(this.props.name);
    }

    getDomain() {
        return this.domain.toList(this.context);
    }

    get sources() {
        return [this.optionsSource];
    }
    get optionsSource() {
        return {
            placeholder: this.env._t("Loading..."),
            options: this.loadOptionsSource.bind(this),
        };
    }

    get activeActions() {
        return this.props.activeActions || {};
    }

    onSelect(option, params = {}) {
        if (option.action) {
            return option.action(params);
        }
        const record = [
            option.value, option.label
        ];
        this.props.update(record, { save: true });
    }

    async update(nextProps) {
        super.update(nextProps);
    }

    async loadOptionsSource(request) {
        if (this.lastProm) {
            this.lastProm.abort(false);
        }
        this.lastProm = this.orm.call(this.props.relation, "search_options", [], {
            name: request,
            operator: "ilike",
            args: this.getDomain(),
            limit: this.props.searchLimit + 1,
            context: this.props.context,
        });
        const records = await this.lastProm;

        const options = records.map((result) => ({
            value: result.id,
            id: result.id,
            label: result.name,
            description: result[this.props.options.description || 'description'],
            image: result[this.props.options.image || 'logo'] ? '/web/image/' + this.props.relation + '/' + result.id + '/' + this.props.options.image || 'logo' : false,
            color: result[this.props.options.color || 'color'],
        }));

        if (!this.props.noSearchMore && this.props.searchLimit < records.length) {
            options.push({
                label: this.env._t("Search More..."),
                action: this.onSearchMore.bind(this, request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            });
        }

        if (!records.length && !this.activeActions.create) {
            options.push({
                label: this.env._t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }

        return options;
    }

    async onSearchMore(request) {
        const { resModel, getDomain, context, fieldString } = this;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                args: domain,
                operator: "ilike",
                limit: this.props.searchMoreLimit,
                context,
            });

            dynamicFilters = [
                {
                    description: sprintf(this.env._t("Quick search: %s"), request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }

        const title = sprintf(this.env._t("Search: %s"), fieldString);
        this.selectCreate({
            domain,
            context,
            filters: dynamicFilters,
            title,
            kanbanViewId: this.props.kanbanViewId,
        });
    }
}

Many2OneImageField.template = "web.Many2OneImageField";
Many2OneImageField.components = {
    Many2OneField,
};
Many2OneImageField.props = {
    ...Many2OneField.props,
    searchLimit: { type: Number, optional: true },
    searchMoreLimit: { type: Number, optional: true },
    noSearchMore: { type: Boolean, optional: true },
    options: { type: Object, optional: true },
    sources: { type: Array, optional: true },
};
Many2OneImageField.defaultProps = {
    searchLimit: 10,
    searchMoreLimit: 320,
    noSearchMore: true,
};

Many2OneImageField.supportedTypes = ["many2one"];

Many2OneImageField.extractProps = ({attrs, field}) => {
    return {
        ...Many2OneField.extractProps({attrs, field}),
        options: attrs.options || {},
    };
};

registry.category('fields').add('many2one_image', Many2OneImageField);