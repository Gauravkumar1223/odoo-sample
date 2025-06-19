/** @odoo-module **/
import { Component, useState, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";

import {useService} from '@web/core/utils/hooks';


import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {_t} from 'web.core';

export class WrrritRefresh extends Component {
    setup() {

        this.rpc = useService('rpc');
        this.pollingInterval = setInterval(this.pollForUpdates.bind(this), 5000);  // Poll every 5 seconds
        this.state = useState({
            value: this.props.value
        });
    }

    async pollForUpdates() {
        try {
            const recordId = this.props.record.data.id;
            const model = this.props.record.resModel;
            const fieldName = this.props.name;

            const { data } = await this.rpc('/web/dataset/call_kw',{
                model: model,
                method: 'read',
                args: [[recordId], [fieldName]],
                kwargs: {},
            });

            const newValue = data[0][fieldName];
            if (newValue !== this.state.value) {
                this.state.value = newValue;
            }
        } catch (error) {
            console.error('Error polling for updates:', error);
        }
    }

    onWillUnmount() {
        clearInterval(this.pollingInterval);  // Clear the interval when the widget is destroyed
    }
}

WrrritRefresh.template = "wrrrit_ai.WrrritRefresh";
WrrritRefresh.props = {
    ...standardFieldProps,

};

registry.category("fields").add("wrrrit_refresh", WrrritRefresh);
