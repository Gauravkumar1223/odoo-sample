/** @odoo-module **/


import {registry} from '@web/core/registry';
import {useService} from '@web/core/utils/hooks';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {_t} from 'web.core';


const {Component, useState, useRef} = owl;

export class LongTaskWidget extends Component {
    setup() {
        super.setup();
        this.options = this.props.options || {};
        this.state = useState({status: 'pending'});
        this.buttonRef = useRef('startButton');
        this.rpc = useService('rpc');
    }

    async startLongTask() {
        const task_id = this.props.options.taskId;
        if (!task_id) {
            console.error("Task ID is missing!");
            return;
        }
        await this.rpc
        ('/long_task/trigger', {
            task_id: task_id
        });

        await this.checkTaskStatus(task_id);
    }

    async checkTaskStatus(task_id) {
        const response = await this.rpc
        ('/long_task/status', {
            task_id: task_id
        });
        this.state.status = response.status;
        if (response.status === 'in_progress') {
            setTimeout(() => this.checkTaskStatus(task_id), 1000);
        }
    }
}

LongTaskWidget.template = 'LongTaskWidget';

LongTaskWidget.props = {
    ...standardFieldProps,
    options: {
        type: Object,
        optional: true
    },
};

LongTaskWidget.extractProps = ({attrs}) => {
    return {
        options: attrs.options || {}
    };
};


registry.category('fields').add('long_task_widget', LongTaskWidget);
