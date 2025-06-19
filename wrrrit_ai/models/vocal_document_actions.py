import concurrent.futures
import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from odoo import models, fields, api, _, SUPERUSER_ID, registry
from .azur_llm_pool import AzurePoolLLM
from .timer_decorator import log_execution_time
from .voice_record_ai_actions import VoiceRecordAiActions

_logger = logging.getLogger(__name__)

# Singleton ThreadPoolExecutor
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
wrrrit_llm = AzurePoolLLM(stream=False)


class ExtendedVoiceRecord(models.Model):
    _name = "wrrrit.ai.voice_record"

    _inherit = ["wrrrit.ai.voice_record", "mail.thread", "mail.activity.mixin"]

    # Add a new field to the voice_record model to track report generation state
    is_report_being_generated = fields.Boolean(
        string="Is Report Being Generated", default=False
    )
    is_content_being_generated = fields.Boolean(
        string="Is Content Being Generated", default=False
    )

    encrypted_field = fields.Char("Encrypted Field")

    def action_rewrite_report(self):
        for record in self:
            formatted_responses = record.generated_report

            rewritting = wrrrit_llm.call_llm([{"role": "system", "content": (
                "Please revise this report while adhering to the given structure and HTML design. "
                "Eliminate any redundancies and fill in missing information in the details fields, "
                "ensuring to maintain the original language throughout. "
                "If any information within brackets is absent, the corresponding line should be omitted. "
                "Number the sections within <div class='section-content'>, do not repeat title, and the information "
                "within each section to enhance the report's fluidity and coherence. "
                "Use Roman numerals for section numbering")},
                                              {"role": "user", "content": formatted_responses}])
            record.generated_report = rewritting

    def action_generate_report_threading(self):
        start_time = time.time()

        start_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Starting Generation of report {self.name}, at {start_time_str}:"
        # self.env['bus.bus']._sendone('wrrrit','wrrrit-progress', {
        #     'type': 'report-progress',
        #     'title': 'Generation Started for Record %s' % self.name,
        #     'progress': 50  #
        # })
        self.send_message_to_current_user(message)
        self.owner_id.partner_id.message_post(
            body=message,
            message_type="notification",
        )

        try:
            _logger.info("Starting action_generate_report for record %s", self.name)
            if self.is_report_being_generated:
                # If the flag is True, return a notification to the client
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Report Generation"),
                        "message": _(
                            "Report generation has already started for record %s."
                            % self.name
                        ),
                        "sticky": False,
                    },
                }
            # Set the flag to True to prevent duplicate report generation
            self.write({"is_report_being_generated": True})
            self._cr.commit()

            _logger.info("Starting report generation for record %s", self.name)
            future = _executor.submit(self._generate_report, self.id)
            future.add_done_callback(self._on_report_done)
            notification_message = _(
                "Starting report generation for record %s at %s."
                % (self.name, start_time_str)
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Report Generation"),
                    "message": notification_message,
                    "sticky": False,
                },
            }
        except Exception as e:
            _logger.error("An error occurred: %s", e)
            self.is_report_being_generated = False
            self._cr.rollback()
            raise

    @log_execution_time()
    def _generate_report(self, record_id):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            try:
                # Create an environment with the new cursor
                env = api.Environment(new_cr, self.env.uid, self.env.context)

                partner_id = env.user.partner_id.id
                _logger.info("### Generating report for partner %d", partner_id)
                record = env["wrrrit.ai.voice_record"].browse(record_id)

                if record.exists():

                    tasks_list = self.create_tasks_from_records(locale="english")

                    generated_report = self.execute_tasks(
                        model_name="wrrrit.ai.voice_record",
                        field_name="generated_report",
                        tasks_list=tasks_list,
                    )

                    # Write using the new environment
                    record.sudo().write(
                        {
                            "generated_report": generated_report,
                            "is_report_being_generated": False,
                        }
                    )
                    #### Create PDF and Docx from generated report
                    try:
                        footer = (
                            record.report_template[0].footer
                            if record.report_template
                            else ""
                        )
                        header = (
                            record.report_template[0].header
                            if record.report_template
                            else ""
                        )
                        logo = (
                            record.report_template[0].logo
                            if record.report_template
                            else ""
                        )

                        pdf_data = VoiceRecordAiActions.text_to_pdf_formatted(
                            generated_report,
                            footer=footer,
                            header=header,
                            logo=logo,
                        )
                        logo = (
                            record.report_template[0].logo
                            if record.report_template
                            else ""
                        )
                        docx_data = VoiceRecordAiActions.html_to_docx_formatted(
                            generated_report,
                            footer=footer,
                            header=header,
                            logo=logo,
                        )

                        record.generated_file = pdf_data
                        record.generated_docx = docx_data
                        formatted_date = datetime.datetime.now().strftime("%y%m%d")
                        sequence_number = (
                                record.env["ir.sequence"].next_by_code(
                                    "wrrrit.ai.voice_record.pdf.sequence"
                                )
                                or "0001"
                        )
                        pdf_filename = (
                            f"{record.name}-{formatted_date}-{sequence_number}.pdf"
                        )
                        docx_filename = (
                            f"{record.name}-{formatted_date}-{sequence_number}.docx"
                        )
                        record.write(
                            {
                                "generated_file_name": pdf_filename,
                                "generated_file": pdf_data,
                                "generated_docx_name": docx_filename,
                                "generated_docx": docx_data,
                            }
                        )
                        report_name = f"{record.name}-{formatted_date}-{sequence_number}-{record.record_locale}"
                        record.env["wrrrit.ai.voice_record.pdf"].create(
                            {
                                "name": report_name,
                                "pdf_report_data": pdf_data,
                                "voice_record_id": record.id,
                            }
                        )
                    except Exception as e:
                        _logger.error(
                            f"An error occurred during report generation for record ID {record.id}: {e}"
                        )

                    new_cr.commit()  # Commit changes in the new cursor
                else:
                    _logger.info("Record ID %d not found.", record_id)
            except Exception as e:
                _logger.error("An error occurred: %s", e)
                new_cr.rollback()
                raise
            finally:
                record.sudo().write(
                    {
                        "generated_report": generated_report,
                        "is_report_being_generated": False,
                    }
                )

                new_cr.close()

    def _on_report_done(self, future):
        """Callback executed when the thread task is completed."""
        record_id = self.id
        dbname = self._cr.dbname

        # Since this method runs in a different thread, use a new cursor
        with registry(dbname).cursor() as new_cr:
            try:
                # Create a new environment with the new cursor
                env = api.Environment(new_cr, SUPERUSER_ID, {})
                # Access the record with the new environment
                record = env["wrrrit.ai.voice_record"].browse(record_id)
                start_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                notification_message = _(
                    "Report generated for record %s at %s."
                    % (record.name, start_time_str)
                )

                with registry(self._cr.dbname).cursor() as new_cr2:
                    new_env = api.Environment(new_cr2, self.env.uid, self.env.context)
                    record2 = new_env["wrrrit.ai.voice_record"].browse(record_id)
                    new_env["bus.bus"]._sendone(
                        new_env.user.partner_id,
                        "simple_notification",
                        {
                            "title": _("Report Generation"),
                            "type": "warning",
                            "sticky": False,
                            "message": notification_message,
                        },
                    )
                    # new_env['bus.bus']._sendone('wrrrit','wrrrit-progress', {
                    #     'type': 'report-progress',
                    #     'title': 'Generation Started for Record %s' % record2.name,
                    #     'progress': 100  #
                    # })

                    start_time_str = datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    message = f"Generation of report  {record2.name} completed at {start_time_str}:"

                    record2.send_message_to_current_user(message)
                    new_cr.commit()

                if future.exception():
                    _logger.error("Report generation failed: %s", future.exception())

                else:
                    # Here, ensure that we use the new environment to write
                    record.sudo().write({"is_report_being_generated": False})
                    _logger.info(
                        "Report generated successfully for record %d", record_id
                    )

                new_cr.commit()
            except Exception as e:
                # It's a good idea to have a broad exception handler to log unexpected exceptions
                _logger.error(" Cursor  unexpected error occurred: %s", e)
                new_cr.rollback()
            finally:
                new_cr.close()  # Always close the cursor explicitly when you're done with i

    def send_message_to_current_user(self, message_body):
        return  # Disable this feature for now
        # The current user is the user that is logged in and making the call
        current_user = self.env.user
        system_user_partner_id = self.env.ref("base.partner_root").id

        subtype_id = self.env.ref("mail.mt_comment").id

        # Find a private channel for the current user, or create one if it doesn't exist
        # Private channels typically have 'uuid' in their name
        channel = self.env["mail.channel"].search(
            [
                ("channel_type", "=", "chat"),
                ("channel_partner_ids", "=", current_user.partner_id.id),
                ("channel_partner_ids", "=", 1),
            ],
            limit=1,
        )

        if not channel:
            # Create a new channel with the current user
            channel = self.env["mail.channel"].create(
                {
                    "name": "Chat with user %s" % current_user.name,
                    "channel_type": "chat",
                    "channel_partner_ids": [
                        (4, current_user.partner_id.id),
                        (4, system_user_partner_id),
                    ],  # (4, id) is for adding to Many2many relation
                }
            )

        # Send the message
        channel.sudo().message_post(
            body=message_body,
            message_type="comment",
            subtype_id=subtype_id,
            author_id=system_user_partner_id,
        )

    def fetch_response(self, system, user, order):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        response = wrrrit_llm.call_llm(messages, max_tokens=4000, temperature=0.0)
        return order, response

    def format_responses(self, ordered_responses):
        formatted_responses = "<div class='sections-container'>"

        for order, response in ordered_responses:
            # Add a header or title if your response doesn't already include one
            header = f""

            # Wrap each response in a div with a class for styling
            div_response = f"<div class='section-content'>{response}</div>"

            # Concatenate header and response, and add a separator
            formatted_responses += (
                f"{header}{div_response}<hr class='section-separator'/>"
            )


        # formatted_responses += "</div>"
        return formatted_responses

    def fetch_response_with_notification(self, system, user, order, total_tasks):
        dbname = self._cr.dbname
        record_id = self.id
        progress = (1 / total_tasks) * 25
        # _logger.info("start task progress is %d", progress)

        # Using a new cursor for this task
        with registry(dbname).cursor() as new_cr:
            env = api.Environment(
                new_cr, self.env.uid, self.env.context
            )  # Create a new environment
            record = env["wrrrit.ai.voice_record"].browse(record_id)
            model_name = "wrrrit.ai.voice_record"  # This should be the actual model name
            channel_name = f"wrrrit-progress-{model_name}"

            # Sending start notification
            env["bus.bus"]._sendone(
                channel_name,
                channel_name,
                {
                    "type": "report-progress",
                    "title": f"Task Started for Record {record.name}",
                    "progress": progress,
                    "model_name": model_name,
                    "record_id": record.id,
                },
            )
            new_cr.commit()  # Commit the transaction to send the notification immediately
            # Actual task execution
            response = self.fetch_response(
                system, user, order
            )  # Replace with the actual method if different

            # Sending end notification

            env["bus.bus"]._sendone(
                channel_name,
                channel_name,
                {
                    "type": "report-progress",
                    "title": f"Task Completed for Record {record.name}",
                    "progress": progress * 3,
                    "model_name": model_name,
                    "record_id": record.id,

                },
            )
            new_cr.commit()
            new_cr.close()
            # Commit to send the notification

        return response

    def execute_tasks_and_notify(self, model_name, field_name, tasks_list):
        total_tasks = len(tasks_list)
        formatted_responses = []
        logging.info("total tasks are %s", total_tasks)

        with ThreadPoolExecutor() as executor:
            # Create a list of futures along with the order index
            future_to_order = {
                executor.submit(
                    self.fetch_response_with_notification,
                    system,
                    user,
                    order,
                    total_tasks,
                ): order
                for order, (user, system) in enumerate(tasks_list)
            }

            for future in as_completed(future_to_order):
                order = future_to_order[future]
                response = future.result()
                formatted_responses.append((order, response))

        # Sort by the original order and format the responses
        formatted_responses.sort(key=lambda x: x[0])
        sorted_responses = [response for _, response in formatted_responses]
        return self.format_responses(sorted_responses)

    def create_tasks_from_records(self, locale="english"):
        try:
            # Initialize the list to store all tasks
            all_tasks = []

            # Loop through records in self
            for record in self:
                # Create a new environment and cursor for each record
                with self.pool.cursor() as new_cr:
                    env = api.Environment(new_cr, self.env.uid, self.env.context)
                    record = env["wrrrit.ai.voice_record"].browse(record.id)
                    locale = record.record_locale or locale
                    # _logger.info("locale is %s", locale)
                    original_transcript_words = len(record.transcription_data.split())
                    corrected_transcript_words = (
                        len(record.corrected_transcription_data.split())
                        if record.corrected_transcription_data
                        else 0
                    )

                    if corrected_transcript_words >= original_transcript_words / 2:
                        context_text = record.corrected_transcription_data
                    else:
                        context_text = record.transcription_data

                    styling = (""" use those classes to style the report:
                    
                                .rep_container: The main container for the report, setting the overall font and layout.
                                .rep_title: Style for the report title, usually larger and bold.
                                .rep_header: Used for section headers within the report, slightly smaller than the title but still prominent.
                                .rep_section: Defines a section in the report, used to group related content.
                                .rep_content: Styles for the main content or body text of the report.
                                .rep_bullets: Used for unordered lists, applying standard bullet points.
                                .rep_bullets li: Individual list items within a .rep_bullets list.
                                .rep_signature: Area for the signature, typically aligned to the right.
                                .rep_signature-line: A horizontal line for the signer to write over.
                                .rep_signature-name: Placeholder for the name of the signer, usually below the signature line.
                                .rep_footer: Footer style, for additional information at the bottom of the report.
                                .rep_table: Basic styling for tables included in the report.
                                .rep_table th, .rep_table td: Styles for table headers and table data cells.
                                .rep_table th: Specific styling for table header cells.
                                .rep_table tr:nth-child(even): Alternate row styling for table rows."""

                               )
                    styling_directive = (f"Apply the following styling to the generated content, and do not prefix "
                                         f"with code markers the output: \n\n {styling}\n\n")

                    # Get the sections from the record's report template, ordered by sequence
                    sections = (
                        record.report_template[0]
                        .prompt_template_id[0]
                        .section_ids.sorted(key=lambda r: r.sequence)
                    )
                    # logging.info("sections are %s", sections)

                    # Initialize the list to store tasks for this record
                    tasks = []

                    # Create tasks for each section
                    for section in sections:
                        date_declaration = f"IMPORTANT Note: Today's Document Date is: {datetime.datetime.now().strftime('%Y-%m-%d')}\n"
                        locale_declaration = (
                            f"IMPORTANT Note: Translate all non-{locale} text,"
                            f"titles, dates, fields, and data to {locale} in all the output, do not omit any translation.\n"
                        )

                        # Generic system prompt
                        system_prompt = (

                            f"IMPORTANT :Use only the following instructions to generate the section content."
                            f"You are a specialized and expert Doctor,"
                            f"You are a doctor assistant transcriptionist and expert translator"

                        )

                        # Construct the user prompt with specific instructions and context
                        user_prompt = (
                            f"Generate the following section content based only on"
                            f"the provided context, RESPECT localization request and instructions."
                            f"\n{locale_declaration}."
                            f"Follow solely these instructions:\n{section.prompt}\n"
                            f"Using the following  formatting pattern:\n{section.extra}\n"
                            f"{styling_directive}\n"
                            f"Consider only data in This is the following context to generate the section content: "
                            f"\n#### Context :\n{context_text}\n####\n"
                        )

                        # Append date note if insert_date is true
                        if record.report_template[0].prompt_template_id[0].insert_date:
                            system_prompt += f"\n{date_declaration}"

                        # Add user_prompt and system_prompt to the tasks list for this record
                        tasks.append([user_prompt, system_prompt])

                    # logging.info("Number of tasks is %s", len(tasks))

                    # Append the tasks for this record to the list of all tasks
                    all_tasks.extend(tasks)
                    new_cr.commit()
                    new_cr.close()

            return all_tasks
        except Exception as e:
            _logger.error(
                f"An error occurred while creating tasks from the records: {e}"
            )
            new_cr.close()
            return None  # Returning None or handle the error as needed

    def execute_tasks(self, model_name, field_name, tasks_list):
        return self.execute_tasks_and_notify(model_name, field_name, tasks_list)

    def correct_transcript_task(self, locale="english"):
        tasks_list = []
        system_prompt = (
            f"You are an advanced medical transcriptionist, specialized in several medical specialities"
            f"like dermatology, cardiology, and neurology. You are tasked with correcting the following transcription."
            f"Write the response solely in this locale : {locale}.\n\n"
            f"Rewrite the provided medical consultation transcription into a clear,"
            f"coherent, and fluid narrative from a third-person perspective. "
            f"The narrative should correct any informal language and organize the dialogue "
            f"into a structured format. Ensure the text flows naturally and maintains the "
            f"essence of the conversation between Dr. and Patient (retrieve names, "
            f"if available, from the conversation) "
            f"Include explanations and clarifications for any medical terms and conditions"
            f" mentioned, making the narrative accessible to the medical audience."
            f"Highlight all drugs or diseases mentioned in the conversation, correct their spelling and naming based"
            f"on the context of the conversation."
            f"Do not omit any information from the original transcription. Avoid redundancies, "
            f"and avoid adding any additional information that is not mentioned in the original transcription."
        )
        for record in self:
            user_prompt = record.transcription_data
            tasks_list = [[user_prompt, system_prompt]]

        return tasks_list

    def action_generate_content_threading(self, model_name, field_name, tasks_list):
        try:
            if self.is_content_being_generated:
                return self._notify_user(
                    "Content generation has already started for record %s." % self.name,
                    "warning",
                )

            self.is_content_being_generated = True
            self._cr.commit()  # Commit to save the flag change

            start_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._notify_user(
                f"Starting content generation for {model_name} record {self.name}, at {start_time_str}",
                "info",
            )

            # Submit the task to the executor
            future = _executor.submit(
                self._generate_content, self.id, model_name, field_name, tasks_list
            )
            future.add_done_callback(
                lambda f: self._on_content_done(f, model_name, field_name)
            )
        except Exception as e:
            _logger.error("An error occurred: %s", e)
            self.is_content_being_generated = False
            self._cr.rollback()
            raise

    @log_execution_time()
    def _generate_content(self, record_id, model_name, field_name, tasks_list):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            try:
                env = api.Environment(new_cr, self.env.uid, self.env.context)
                record = env[model_name].browse(record_id)

                if record.exists():
                    generated_content = self.execute_tasks(
                        model_name, field_name, tasks_list
                    )  # Implement this method as per your logic
                    record.sudo().write(
                        {
                            field_name: generated_content,
                            "is_content_being_generated": False,
                        }
                    )
                    new_cr.commit()
                else:
                    _logger.info("%s Record ID %d not found.", model_name, record_id)
            except Exception as e:
                _logger.error("An error occurred: %s", e)
                new_cr.rollback()
                raise
            finally:
                new_cr.close()

    def _on_content_done(self, future, model_name, field_name):
        record_id = self.id
        dbname = self._cr.dbname

        with registry(dbname).cursor() as new_cr:
            try:
                env = api.Environment(new_cr, SUPERUSER_ID, {})
                record = env[model_name].browse(record_id)

                if future.exception():
                    _logger.error("Content generation failed: %s", future.exception())
                else:
                    record.sudo().write({"is_content_being_generated": False})
                    _logger.info(
                        "Content generated successfully for %s record %d",
                        model_name,
                        record_id,
                    )
                    self._notify_user(
                        "Content generation completed for record %s." % record.name,
                        "success",
                    )

                new_cr.commit()
            except Exception as e:
                _logger.error("Cursor unexpected error occurred: %s", e)
                new_cr.rollback()
            finally:
                new_cr.close()

    def _notify_user(self, message, message_type):
        with registry(self._cr.dbname).cursor() as new_cr:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            new_env["bus.bus"]._sendone(
                new_env.user.partner_id,
                "simple_notification",
                {
                    "title": _("Content Generation"),
                    "type": message_type,
                    "sticky": False,
                    "message": message,
                },
            )
            new_cr.commit()

    def action_voice_record_correct_transcript(self):
        for record in self:
            locale = record.record_locale or "english"
            tasks_list = self.correct_transcript_task(locale=locale)

            self.action_generate_content_threading(
                field_name="corrected_transcription_data",
                model_name="wrrrit.ai.voice_record",
                tasks_list=tasks_list,
            )

    def generate_pdf(self):
        for record in self:
            if not record.generated_report:
                return

            footer = (
                record.report_template[0].footer
                if record.report_template
                else ""
            )
            header = (
                record.report_template[0].header
                if record.report_template
                else ""
            )
            logo = (
                record.report_template[0].logo
                if record.report_template
                else ""
            )

            pdf_data = VoiceRecordAiActions.text_to_pdf_formatted(
                record.generated_report,
                footer=footer,
                header=header,
                logo=logo,
            )
            logo = (
                record.report_template[0].logo
                if record.report_template
                else ""
            )
            docx_data = VoiceRecordAiActions.html_to_docx_formatted(
                record.generated_report,
                footer=footer,
                header=header,
                logo=logo,
            )

            record.generated_file = pdf_data
            record.generated_docx = docx_data
            formatted_date = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = (
                    record.env["ir.sequence"].next_by_code(
                        "wrrrit.ai.voice_record.pdf.sequence"
                    )
                    or "0001"
            )
            pdf_filename = (
                f"{record.name}-{formatted_date}-{sequence_number}.pdf"
            )
            docx_filename = (
                f"{record.name}-{formatted_date}-{sequence_number}.docx"
            )
            record.write(
                {
                    "generated_file_name": pdf_filename,
                    "generated_file": pdf_data,
                    "generated_docx_name": docx_filename,
                    "generated_docx": docx_data,
                }
            )
            report_name = f"{record.name}-{formatted_date}-{sequence_number}-{record.record_locale}"
            record.env["wrrrit.ai.voice_record.pdf"].create(
                {
                    "name": report_name,
                    "pdf_report_data": pdf_data,
                    "voice_record_id": record.id,
                }
            )
            # refresh the view
            return {
                "type": "ir.actions.client",
                "tag": "reload",
            }