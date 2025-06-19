import json
import logging
from concurrent.futures import as_completed, ThreadPoolExecutor

from odoo import models, fields, api, registry, _
from .mint_llm_pool import MintPoolLLM

_logger = logging.getLogger(__name__)


class MintDocument(models.Model):
    _name = "mint.document"
    _description = "DocuMint AI Document"
    _order = "id desc"  # Orders by most recently created first

    # Computed field for the document name
    name = fields.Char(
        string="Title", compute="_compute_name", store=True, readonly=False
    )
    title = fields.Char(string="User Title")  # Field for user's input
    prompt = fields.Text(string="Prompt", default="Generate 4 chapters, including introduction and conclusion")
    description = fields.Text(string="Description")
    content_structure = fields.Text(string="Content Structure")
    locale = fields.Selection([("english", "English"), ("french", "French"), ("german", "German")], string="Language",
                              default="english")
    chapter_ids = fields.One2many("mint.chapter", "document_id", string="Chapters")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="draft",
        string="State",
    )
    is_content_being_generated = fields.Boolean(
        string="Is Content Being Generated?", default=False
    )

    content = fields.Text(string="Content")
    content_generated = fields.Text(string="Generated Content")
    # Fields for tracking file versions
    pdf_attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[
            ("res_model", "=", "mint.document"),
            ("mimetype", "=", "application/pdf"),
        ],
        string="PDF Versions",
    )
    docx_attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[
            ("res_model", "=", "mint.document"),
            (
                "mimetype",
                "in",
                [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/msword",
                ],
            ),
        ],
        string="DOCX Versions",
    )
    md_attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[
            ("res_model", "=", "mint.document"),
            ("mimetype", "=", "text/markdown"),
        ],
        string="Markdown Versions",
    )

    @api.depends("title")
    def _compute_name(self):
        for record in self:
            record.name = record.title or f"Document-{record.id}"

    # Initiate one MintPoolLLM instance to be shared by all documents
    mint_llm_pool = MintPoolLLM(
        stream=False
    )  # The parameters like max_tokens_model will be those provided during class initialization

    def action_generate_description(self):
        for record in self:
            # Your logic to generate the description for each document record
            pre_prompt = record.prompt or "Generate 4 chapters, including introduction and conclusion. "
            pre_prompt = pre_prompt + self.generate_system_prompt()
            description_prompt, _ = self._preprocess_prompts(pre_prompt, "")
            messages = [
                {"role": "system", "content": description_prompt},
                {
                    "role": "user",
                    "content": record.title or "Python for Beginners",
                },
            ]
            response_content = record.mint_llm_pool.call_llm(messages)
            if response_content:
                record.description = response_content
                record.content_structure = record.generate_document_structure()

    def action_generate_chapters(self):
        for record in self:
            record.create_chapters_from_response(record.description)

    def generate_content_prompt(self):
        content_prompt = """
As a skilled typewriter with expertise in content creation, focus on producing clear, 
concise, and well-structured HTML content. Your task is to develop structured content 
within a <div> tag, suitable for any generic context - be it a section, chapter, or a 
specific topic. Adhere strictly to the topic provided, ensuring factual accuracy and 
coherence. Your writing should be error-free, with proper formatting and punctuation, 
and maintain a formal, professional tone. Organize the HTML content logically, using 
appropriate headers, paragraphs, and lists. Here is a sample HTML template to guide you:
<div style="font-family: Arial, sans-serif; color: #333;">
  
    <h2 style="color: #2a71d0; font-weight: normal;  margin-left: 5px;">[Chapter or Section Title and Number]</h2>
    <p style="font-size: 16px; margin-left: 7px;">Introductory paragraph about the chapter or section.</p>
    <h3 style="color: #2d8f5e; font-weight: lighter; margin-left: 10px;">[Subsection Number and Title]</h3>
    <p style="font-size: 16px; line-height: 1.6;"margin-left: 12px;>Detailed paragraph for the subsection.</p>
    <ul style="list-style-type: disc; margin-left: 20px;">
        <li style="font-size: 16px; color: #555;">Key point or topic detail.</li>
        <li style="font-size: 16px; color: #555;">Another important point.</li>
        <!-- Add more list items as needed -->
    </ul>
    <!-- Include additional subsections or chapters as necessary -->
</div>

"""

        return content_prompt

    def generate_system_prompt(self):
        system_prompt = """
        Act as a proficient typewriter, ensuring that your writing is clear, 
        concise, and well-structured. 
        Adhere strictly to the provided topic, 
        maintaining factual coherence and an error-free presentation. 
        Your writing should exhibit proper formatting, 
        punctuation, and use a formal, professional tone. 
        Organize the content logically, comprising an introduction, body, and conclusion.
        Pay close attention to the user's specific requirements, 
        including desired tones or styles, to customize the material appropriately.
        When generating responses, structure them in JSON format. 
        The structure should include mandatory chapters 'Abstract Summary', 'Introduction', and user-defined chapters.
        Each chapter title must incorporate the chapter number, 
        and each section title should include the corresponding section number.
        Guidance for writing each chapter or section is provided within the 'content' field. 
        The format for this structure is as follows:
        {
          "chapters": [
            {
              "title": "Chapter 1: Abstract Summary",
              "sections": [
                {
                  "title": "Section 1: Overview",
                  "content": "Provide a concise summary of the document’s content, highlighting the key points, findings, and conclusions. This section should give readers a clear idea of what the document covers, without going into detail."
                }
                // Additional sections can be added as needed
              ]
            },
            {
              "title": "Chapter 2: Introduction",
              "sections": [
                {
                  "title": "Section 1: Purpose Statement",
                  "content": "Explain the primary objectives and intentions of the Section. Clarify what the reader
                   should expect to learn or understand by the end of the section."
                },
                {
                  "title": "Section 2: Background Context",
                  "content": "Provide necessary background information or context about the Subject. This may include 
                  historical background, current relevance, or definitions of key terms."
                },
                {
                  "title": "Section 3: Scope",
                  "content": "Define the scope of your analysis or discussion. Clarify the boundaries of the topic, including what is and is not covered."
                },
                {
                  "title": "Section 4: Significance",
                  "content": "Discuss why this topic is important. Highlight the significance of the topic in its broader context, or its relevance to specific fields or areas of interest."
                }
              ]
            },
            // Additional user-defined chapters can be added as required, with similar guidance in their 'content' fields
          
           {
              "title": "Chapter 4: Chapter Title",
              "sections": [
                {
                  "title": "Section 1: [Section Title]",
                  "content": "Describe [Section Content]"
                // Additional sections can be added as needed
              ]
            },
                 // Additional user-defined chapters can be added as required, with similar guidance in their 'content' fields
       
          ]
        }
        """

        return system_prompt

    def create_chapters_from_response(self, content_description):
        _logger.info("Starting to create chapters and sections from response...")

        try:
            document_structure = json.loads(content_description)
        except json.JSONDecodeError as e:
            _logger.error(f"Error decoding JSON response: {e}")
            return

        _logger.info(
            f"Processing total chapters: {len(document_structure.get('chapters', []))}"
        )

        for chapter_index, chapter_data in enumerate(
                document_structure.get("chapters", []), start=1
        ):
            try:
                chapter_record = self.env["mint.chapter"].create(
                    {
                        "name": chapter_data.get(
                            "title", f"Chapter {chapter_index}"
                        ),
                        "locale": self.locale or "english",
                        "document_id": self.id,
                        "sequence": chapter_index * 10,
                    }
                )
                _logger.info(f"Chapter: {chapter_record.name}")

                sections_data = chapter_data.get("sections", [])
                _logger.info(
                    f"Processing total sections in chapter {chapter_record.name}: {len(sections_data)}"
                )

                for section_index, section_data in enumerate(sections_data, start=1):
                    try:
                        section_record = self.env["mint.section"].create(
                            {
                                "name": section_data.get(
                                    "title", f"Section {section_index}"
                                ),
                                "locale": self.locale or "english",
                                "content": section_data.get("content", "N/A"),
                                "chapter_id": chapter_record.id,
                                "sequence": section_index * 10,
                            }
                        )
                        _logger.info(
                            f"Created section: {section_record.name} in chapter: {chapter_record.name}"
                        )
                    except Exception as e:
                        _logger.error(
                            f"Error creating section: {section_data.get('title', f'Generated Section {section_index}')} in chapter: {chapter_record.name}, error: {e}"
                        )
            except Exception as e:
                _logger.error(
                    f"Error creating chapter: {chapter_data.get('title', f'Generated Chapter {chapter_index}')}, error: {e}"
                )

        _logger.info("Finished creating chapters and sections from Description.")

    def action_generate_section_contents(self):
        self.ensure_one()  # Ensure that we're working with a single record
        # Trigger the method to generate section contents
        self.generate_section_contents()
        # You may want to return an action, such as refreshing the view or showing a notification

    def log_document_structure(self):
        self.ensure_one()  # Ensure that we're dealing with a single record
        _logger.info(
            "Logging document structure and attributes for document ID: %s" % self.id
        )

        doc_attributes = {
            "Document ID": self.id,
            "Title": self.title,
            "Description": self.description,
            "Language": self.locale,
            "State": self.state,
            "Total Chapters": len(self.chapter_ids),
        }

        # Log the document's attributes
        for attr_name, attr_value in doc_attributes.items():
            _logger.info("%s: %s" % (attr_name, attr_value))

        # Log each chapter and its sections
        for chapter in self.chapter_ids:
            _logger.info(
                "Chapter: %s (sequence: %s)" % (chapter.name, chapter.sequence)
            )
            for section in chapter.section_ids:
                _logger.info(
                    "\tSection: %s (sequence: %s)" % (section.name, section.sequence)
                )
                _logger.info(
                    "\t\tContent: %s" % section.content[:30]
                )  # Log first 30 chars of content

    def generate_prompt_for_section(self, chapter, section):
        # Title will be used from the chapter record
        # Use the content of the section, if it has any, else use the section title as a fallback
        content_to_expand =" Section:" + section.name + "\n Section Content: " + section.content + "\n"
        content_to_expand = self._preprocess_prompts(content_to_expand, "")
        return (self.generate_content_prompt() + f" '{content_to_expand}'  in '{chapter.name}' and '{self.title}'. in"
                + f"the context of this global document structure'{self.generate_document_structure()}'")

        # Updated call_content_generation_service method

    def generate_section_contents(self):

        locale = self.locale or "english"
        locale_prompt = ("IMPORTANT: Generate and translate all content to: " + locale + ".\n")

        chapters = self.chapter_ids
        tasks = []
        tasks = self.create_task_list(chapters)
        self.send_message_to_current_user("Generating Chapters Task for the document.")
        for chapter in self.chapter_ids:
            # Generate content for the chapter
            chapter_prompt = locale_prompt + self.generate_content_prompt() + f"{chapter.name}'." + f" '{chapter.content}'" + (
                    f" for the document with this plan:" +
                    f"{self.generate_document_structure()}")
            chapter.prompt = chapter_prompt

            sections = chapter.section_ids

            tasks += self.create_task_list(sections)

            self.send_message_to_current_user(
                f"Generating Sections Task for the document: {chapter.name}"
            )
            for section in chapter.section_ids:
                # Use chapter generated_content for generating section content
                section_prompt = locale_prompt + self.generate_prompt_for_section(chapter, section)
                section.prompt = section_prompt

            _logger.info(f"Created :\n {tasks}")

    def create_task_list(self, records):
        """
        Creates a list of tasks with prompts for the system and user assistant roles,
        ordered by the sequence provided in the records.

        :param records: A recordset containing the records to process.
        :return: A list of dicts representing tasks to be processed by the LLM.
        """
        task_list = []

        for record in records.sorted(key=lambda r: r.sequence):
            # Construct system and user prompts here. Modify as needed.
            system_prompt = self._construct_system_prompt_for_record(
                record
            )  # Custom method for system prompt
            user_prompt = self._construct_user_prompt_for_record(
                record
            )  # Custom method for user prompt

            # Check the length, truncate if necessary, handle edge cases
            system_prompt, user_prompt = self._preprocess_prompts(
                system_prompt, user_prompt
            )

            task = {
                "record_id": record.id,  # Renamed 'id' to 'record_id' to clarify its use
                "record.type": record._name,  # Renamed 'model' to 'record.type' to clarify its use
                "order": record.sequence,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            task_list.append(task)
            _logger.info(f"Created task for record ID: {record.id}")
            _logger.info(f"Task: {task}")
        _logger.info(f"Created {len(task_list)} tasks.")
        return task_list

    def _construct_system_prompt_for_record(self, record):
        """
        Constructs a system prompt based on the record data.
        """
        # Placeholder method. Implement based on specific logic required for system prompt creation.
        return self.generate_content_prompt()

    def _construct_user_prompt_for_record(self, record):
        """
        Constructs a user prompt based on the record data.
        """
        # Placeholder method. Implement based on specific logic required for user prompt creation.
        user_prompt = (
                self.generate_content_prompt() +
                f"Please provide a detailed explanation for the topic '{record.name}'.\n"
                f"Apply User instructions: {record.prompt}\n\n Context: {record.content}"
        )
        return user_prompt

    def _preprocess_prompts(self, system_prompt, user_prompt):

        import datetime
        _logger.info("Preprocessing prompts for record ID: %s" % self._name)

        date_prompt = (
                " Note: Today date is "
                + datetime.datetime.today().strftime("%Y-%m-%d")
                + " .\n"
        )

        system_prompt = date_prompt + system_prompt
        user_prompt = date_prompt + user_prompt
        return system_prompt, user_prompt

    def send_message_to_current_user(self, message_body):
        logging.info("Sending message to current user...")

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

            # Sending start notification
            env["bus.bus"]._sendone(
                "wrrrit",
                "wrrrit-progress",
                {
                    "type": "report-progress",
                    "title": f"Task Started for Record {record.name}",
                    "progress": progress,
                },
            )
            new_cr.commit()  # Commit the transaction to send the notification immediately
            # Actual task execution
            response = self.fetch_response(
                system, user, order
            )  # Replace with the actual method if different

            # Sending end notification

            env["bus.bus"]._sendone(
                "wrrrit",
                "wrrrit-progress",
                {
                    "type": "report-progress",
                    "title": f"Task Completed for Record {record.name}",
                    "progress": progress * 3,
                },
            )
            new_cr.commit()
            new_cr.close()
            # Commit to send the notification

        return response

    def execute_tasks(self, model_name, field_name, tasks_list):
        return self.execute_tasks_and_notify(model_name, field_name, tasks_list)

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

    def generate_full_content(self):
        # Creates the full content by combining chapter and section content
        self.ensure_one()

        full_content = ""
        for chapter in self.chapter_ids:
            # Add chapter title and content to the full content
            chapter_content = f" {chapter.content_generated}\n\n"
            full_content += chapter_content

            for section in chapter.section_ids:
                # Add each section's title and content to the full content under its chapter
                section_content = f"{section.content_generated}\n\n"
                full_content += section_content

            # Add some separation between chapters if desired
            full_content += "\n\n"

        # Update the document's content_generated field with the aggregated content
        self.content_generated = full_content
        self.env.cr.commit()  # Commit changes to the database

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

    def fetch_response(self, system, user, order):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        response = self.mint_llm_pool.call_llm(messages, max_tokens=6000, temperature=0.0)
        return order, response

    def format_responses(self, ordered_responses):
        formatted_responses = "<div class='sections-container'>"

        for order, response in ordered_responses:
            # Add a header or title if your response doesn't already include one
            header = f"<h2 class='section-header'> </h2>"

            # Wrap each response in a div with a class for styling
            div_response = f"<div class='section-content'>{response}</div>"

            # Concatenate header and response, and add a separator
            formatted_responses += (
                f"{header}{div_response}<hr class='section-separator'>"
            )

        formatted_responses += "</div>"
        return formatted_responses

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

    # Add this to the MintDocument class

    @api.model
    def generate_content_for_record(self, record_type, record, system_prompt, user_prompt):
        """
        Generates content for a given chapter or section record and stores the resulting content.
        """
        # Note: You may want to adjust this based on how your LLM handles prompts or if you
        # need additional parameters. You may also integrate JSON serialization if needed.


        system_prompt, user_prompt = self._preprocess_prompts(system_prompt, user_prompt)

        response = self.mint_llm_pool.call_llm([{"role": "system", "content": system_prompt},
                                                {"role": "user", "content": user_prompt}])
        if response:
            record.write({'content_generated': response})

    def action_generate_all_content(self):
        """
        This method is meant to be triggered by the user, for example through a button in the interface.
        It aggregates all tasks for chapters and sections and starts the threading process to generate content.
        """
        for doc in self:
            tasks = []
            for chapter in doc.chapter_ids:
                system_prompt = self._construct_system_prompt_for_record(chapter)
                user_prompt = self._construct_user_prompt_for_record(chapter)
                tasks.append((chapter, system_prompt, user_prompt))

                for section in chapter.section_ids:
                    system_prompt = self._construct_system_prompt_for_record(section)
                    user_prompt = self._construct_user_prompt_for_record(section)
                    tasks.append((section, system_prompt, user_prompt))

            futures = []
            with ThreadPoolExecutor() as executor:
                for record, system_prompt, user_prompt in tasks:
                    record_type = 'mint.chapter' if record._name == 'mint.chapter' else 'mint.section'
                    future = executor.submit(
                        self.generate_content_for_record, record_type, record, system_prompt, user_prompt
                    )
                    future.add_done_callback(self._on_content_done)
                    futures.append(future)

            # Wait for all futures to complete
            for future in futures:
                future.result()  # This will wait for each future to complete and will raise any exceptions that occurred.

            # After all futures have completed, we can do any post-completion work.
            self.is_content_being_generated = False
            self.generate_full_content()
            self.env.cr.commit()

            # Notify the user all tasks are complete
            self._notify_user(
                _(f"All content has been generated for the document:{doc.name}"),
                "success",
            )

    def _on_content_done(self, future):
        """
        Callback function that is called once the content generation for a task has finished.
        """
        if future.exception():
            _logger.error("Failed to generate content: %s", future.exception())

    def generate_document_structure(self):
        """
        Generates a tabbed text representation of the document structure
        based on the JSON formatted description field.
        """
        self.ensure_one()  # Ensure we're dealing with a single record
        if not self.description:
            _logger.info("No description available to generate document structure.")
            return "No description available."

        try:
            document_structure = json.loads(self.description)
        except json.JSONDecodeError as e:
            _logger.error(f"Error decoding JSON description: {e}")
            return "Invalid JSON format in description."

        tabbed_text = self._generate_tabbed_structure(document_structure)
        return tabbed_text

    def _generate_tabbed_structure(self, structure):
        """
        Helper method to create a tabbed text structure from the JSON data.
        """
        tabbed_text = ""
        for chapter in structure.get('chapters', []):
            chapter_title = chapter.get('title', 'Untitled Chapter')
            tabbed_text += chapter_title + '\n'

            for section in chapter.get('sections', []):
                section_title = section.get('title', 'Untitled Section')
                tabbed_text += "\t" + section_title + '\n'

                # If there's further nesting, you can continue with more loops and tabs

        return tabbed_text
