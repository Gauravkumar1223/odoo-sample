//** @odoo-module **/
import {Component, onMounted, useState} from '@odoo/owl';
import {registry} from '@web/core/registry';
import {useService} from '@web/core/utils/hooks';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {_t} from 'web.core';

let recorder, gumStream, chunks = [];

export class VoiceRecorder extends Component {

    setup() {
        this.rpc = useService('rpc');
        this.notification = useService('notification');

        this.transcribeFieldName = this.props.transcription;
        this.modelName = this.props.record.resModel || 'wrrrit.ai.voice_record';

        this.state = useState({
            recording: false,
            audioURL: null,
            audioPlaying: false,
            transcribed: this.props.record.data[this.transcribeFieldName]
        });

        onMounted(() => {
            this.loadRecording();
        });
    }

    async loadRecording() {
        const modelName = this.modelName;
        const fieldName = this.props.name;

        if (this.props.record && this.props.record.data) {
            try {
                const voiceRecord = await this.rpc('/web/dataset/call_kw', {
                    model: modelName,
                    method: 'read',
                    args: [this.props.record.data.id, [fieldName]],
                    kwargs: {},
                });

                if (voiceRecord && voiceRecord.length && typeof voiceRecord[0][fieldName] === 'string') {
                    const audioBlob = this.base64ToBlob(voiceRecord[0][fieldName]);
                    if (audioBlob instanceof Blob) {
                        this.state.audioURL = URL.createObjectURL(audioBlob);
                        this.state.hasRecording = true;
                    } else {
                        this.state.hasRecording = false;
                        this.notification.add(_t("Error loading voice recording."), {type: 'danger', sticky: true});
                    }
                }
            } catch (error) {
                this.notification.add(_t("Failed to load voice recording from server."), {type: 'danger', sticky: true});
            }
        }
    }

    padBase64(base64String) {
        while (base64String.length % 4 !== 0) {
            base64String += '=';
        }
        return base64String;
    }

    base64ToBlob(base64) {
        if (!base64) return null;
        let data = atob(this.padBase64(base64));
        let bytes = new Uint8Array(data.length);
        for (let i = 0; i < data.length; i++) {
            bytes[i] = data.charCodeAt(i);
        }
        return new Blob([bytes], {type: 'audio/mp3'});
    }

    async saveRecording(blob) {
        const fieldName = this.props.name;
        const modelName = this.modelName;
        const reader = new FileReader();
        return new Promise((resolve, reject) => {
            reader.onloadend = async () => {
                let base64data = reader.result;
                base64data = base64data.split(',')[1];

                try {
                    const result = await this.rpc('/web/dataset/call_kw', {
                        model: modelName,
                        method: 'write',
                        args: [[this.props.record.data.id], {[fieldName]: base64data}],
                        kwargs: {},
                    });
                    resolve(result);
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    async recordVoice() {
        if (this.state.recording) {
            recorder.stop();
            gumStream.getAudioTracks()[0].stop();
            this.state.recording = false;
        } else {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({audio: true});
                gumStream = stream;

                if (!recorder || recorder.state === 'inactive') {
                    chunks = [];
                    recorder = new MediaRecorder(stream);
                }

                recorder.ondataavailable = (event) => {
                    chunks.push(event.data);
                };

                recorder.onstop = async () => {
                    const blob = new Blob(chunks, {type: 'audio/mp3'});
                    this.state.audioURL = URL.createObjectURL(blob);
                    try {
                        await this.saveRecording(blob);
                        this.notification.add(_t("Recording saved successfully."), {type: 'info', sticky: false});
                    } catch (error) {
                        this.notification.add(_t("Error saving recording."), {type: 'danger', sticky: true});
                    }
                };

                recorder.start();
                this.state.recording = true;
            } catch (error) {
                this.notification.add(_t("Error accessing microphone."), {type: 'danger', sticky: true});
            }
        }
    }

    playRecording() {
        if (!this.state.audioPlaying && this.state.audioURL) {
            let audio = new Audio(this.state.audioURL);
            audio.onended = () => {
                this.state.audioPlaying = false;
            };
            audio.play();
            this.state.audioPlaying = true;
        }
    }

       pauseAudio() {
        console.log('Pausing Audio');
        if (this.audio && !this.audio.paused) {
            this.audio.pause();
        }
    }

    restartAudio() {
        console.log('Restarting Audio');
        if (this.audio) {
            this.audio.currentTime = 0;
            this.audio.play();
        }
    }

    stopRecording() {
        console.log('Stopping Recording');
        if (recorder && recorder.state === 'recording') {
            recorder.stop();
            gumStream.getAudioTracks()[0].stop();
            this.state.recording = false;
        }
    }

    async deleteRecording() {
        const fieldName = this.props.name;
        const modelName = this.modelName;
        // console.log('deleteRecording called for record:', this.props.record);
        if (this.props.record && this.props.record.data) {
            const result = await this.rpc('/web/dataset/call_kw', {
                model: modelName,
                method: 'write',
                args: [[this.props.record.data.id], {[fieldName]: null}],
                kwargs: {},
            });
            // console.log('deleteRecording RPC response:', result);
            this.state.transcribed = "";
            this.state.audioURL = null;
        }
    }

    mounted() {
        // console.log('Component mounted. Loading recording.');
        this.loadRecording();
    }

}

VoiceRecorder.template = 'wrrrit_ai.VoiceRecorder';
VoiceRecorder.props = {
    ...standardFieldProps,
    model: {type: String, optional: true},
    voice: {type: String, optional: true},
    transcription: {type: String, optional: true},
};
VoiceRecorder.extractProps = ({attrs}) => {
    return {
        model: attrs.options.model,
        voice: attrs.options.voice,
        transcription: attrs.options.transcription
    };
};
VoiceRecorder.supportedTypes = ['binary'];
registry.category('fields').add('wrrrit_recorder', VoiceRecorder);
