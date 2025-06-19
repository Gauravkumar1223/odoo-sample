import base64
import io
import mimetypes
import langchain
import openai
import pytesseract
from PIL import Image
from langchain.memory import ConversationBufferMemory
from pdf2image import convert_from_bytes

from odoo.exceptions import UserError
from . import prompts
from odoo import models, fields, api, _
import logging
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

from .azure_llm import AzureLLM
from .documents_ai_actions import DocumentAiActions

from .voice_record_ai_actions import VoiceRecordAiActions

_logger = logging.getLogger(__name__)


class MedicalDocument(models.Model):
    _name = "wrrrit.ai.medical.document"
    _description = "Medical Document"

    name = fields.Char(string="Name", required=True, default="Medical Document")
    file_name = fields.Char(string="File Name", default="Medical Document")
    description = fields.Text(string="Description")
    generated_report = fields.Text(string="Generated Report")

    @api.model
    def _default_owner(self):
        return self.env.user

    is_user_admin = fields.Boolean(search="_search_is_user_admin")

    def _search_is_user_admin(self, operator, value):
        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise UserError(_("Invalid search operator or value for is_user_admin"))
        is_true = (operator == "=" and value) or (operator != "=" and not value)
        user_is_admin = self.env.user.has_group("base.group_system")
        if (is_true and user_is_admin) or (not is_true and not user_is_admin):
            _logger.info("User is admin")
            return []  # Return an empty domain to match all records
        else:
            _logger.info("User is not admin")
            return [("id", "=", 0)]  # Return a domain to match no records

    owner_id = fields.Many2one("res.users", string="Owner", default=_default_owner)

    generated_file = fields.Binary("Generated PDF Report", attachment=False)
    pdf_reports = fields.One2many(
        "wrrrit.ai.voice_record.pdf", "medical_document_id", string="Generated Reports"
    )

    creation_date = fields.Datetime(string="Creation Date", default=fields.Datetime.now)
    extracted_text = fields.Text(string="Extracted Text")
    extracted_metadata = fields.Text(string="Meta Extracted")

    @api.model
    def _get_default_locale(self):
        # Get the user's language (e.g., "en_US")
        user_lang = self.env.user.lang

        # Extract the language part (e.g., "en")
        lang_part = user_lang.split("_")[0] if user_lang else ""

        # Map to your field values
        lang_map = {
            "en": "english",
            "de": "german",
            "fr": "french",
            "it": "italian",
            "es": "spanish",
            "pt": "portuguese",
            "nl": "dutch",
            "tr": "turkish",
            "ar": "arabic",
        }

        return lang_map.get(lang_part, "english")  # Default to 'english' if no match

    record_locale = fields.Selection(
        [
            ("english", "Generate English"),
            ("german", "Generate German"),
            ("french", "Générer du Français"),
            ("italian", "Generare Italiano"),
            ("spanish", "Generar Español"),
            ("portuguese", "Gerar Português"),
            ("dutch", "Genereren in het Nederlands"),
            ("turkish", "Yazılımı Türkçe Yaz"),
            ("arabic", "توليد اللغة العربية"),
        ],
        string="Report Language",
        default=_get_default_locale,
    )

    @api.model
    def _default_report_template(self):
        return self.env["wrrrit.ai.report"].search([], limit=1)

    report_template = fields.Many2one(
        "wrrrit.ai.report",
        string="Record Report Template",
        default=_default_report_template,
        #alias="report_template",
    )
    file_data = fields.Binary(string="File Data")
    file_type = fields.Char(string="File Type")
    last_update = fields.Datetime(string="Last Update", default=fields.Datetime.now)
    is_pdf = fields.Boolean(compute="_compute_file_type", default=False)
    is_image = fields.Boolean(compute="_compute_file_type", default=False)
    is_txt = fields.Boolean(compute="_compute_file_type", default=False)
    is_docx = fields.Boolean(compute="_compute_file_type", default=False)
    is_audio = fields.Boolean(compute="_compute_file_type", default=False)
    is_ocr_done = fields.Boolean(string="Is OCR Done", default=False)
    medical_document_id = fields.Many2one(
        "wrrrit.ai.document", string="Medical Documents"
    )

    @api.depends("file_type", "file_data")
    def _compute_file_type(self):
        for record in self:
            record.is_pdf = record.file_type == "application/pdf"
            record.is_image = record.file_type in ["image/png", "image/jpeg"]
            record.is_txt = record.file_type == "text/plain"
            record.is_docx = (
                record.file_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            record.is_audio = record.file_type in [
                "audio/mpeg",
                "audio/wav",
                "audio/ogg",
            ]

    @api.model
    def create(self, vals):
        try:
            file_name = vals.get("file_name")
            name_prefix = fields.Datetime.now().strftime("%Y-%m-%d")
            sequence = self.env["ir.sequence"].next_by_code("medical.document.sequence")

            # If file_name is provided, use it to generate the name.
            # Otherwise, just use the prefix and sequence.
            if file_name:
                vals["name"] = f"{name_prefix}-{sequence}-{file_name.rsplit('.', 1)[0]}"
            else:
                vals["name"] = f"{name_prefix}-{sequence}"

            _logger.info(f'Creating medical document: {vals["name"]}')

            return super(MedicalDocument, self).create(vals)
        except Exception as e:
            _logger.error(f"Error creating medical document: {str(e)}")
            raise

    @api.onchange("file_name", "file_data", "is_ocr_done")
    def _onchange_file_name(self):
        for record in self:
            # Set is_ocr_done to False since file_name or file_data has changed
            record.is_ocr_done = False

            # Attempt to guess the MIME type of the file
            mime_type, encoding = mimetypes.guess_type(record.file_name)
            record.file_type = mime_type

            # Log MIME type information
            _logger.info(
                f"Record ID {record.id}: File MIME type detected as {mime_type}"
            )

            try:
                file_name = record.file_name
                name_prefix = fields.Datetime.now().strftime("%Y-%m-%d")
                sequence = self.env["ir.sequence"].next_by_code(
                    "medical.document.sequence"
                )

                # Determine the new name for the record based on the provided file_name
                new_name = (
                    f"{name_prefix}-{sequence}-{file_name.rsplit('.', 1)[0]}"
                    if file_name
                    else f"{name_prefix}-{sequence}"
                )
                record.name = new_name

                # Log new name information
                _logger.info(f"Record ID {record.id}: New name set as {new_name}")

                # Update file type flags based on the detected MIME type
                record.is_pdf = record.file_type == "application/pdf"
                record.is_image = record.file_type in ["image/png", "image/jpeg"]
                record.is_txt = record.file_type == "text/plain"
                record.is_docx = (
                    record.file_type
                    == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                record.is_audio = record.file_type in [
                    "audio/mpeg",
                    "audio/wav",
                    "audio/ogg",
                ]

                # Log file type flag updates
                _logger.info(f"Record ID {record.id}: File type flags updated.")

            except Exception as e:
                # Log error with more context
                _logger.error(
                    f"Record ID {record.id}: Error renaming medical document - {str(e)}"
                )
                raise

            # Log the end of processing for this record
            _logger.info(f"Record ID {record.id}: Refreshing document.")

    def action_ocr_document(self):
        config = ""
        for record in self:
            _logger.info(f"Record ID {record.id}: is_ocr_done = {record.is_ocr_done}")

            if (not record.is_ocr_done) and record.file_data:
                try:
                    _logger.info("Processing record ID %s: Decoding file.", record.id)
                    data = base64.b64decode(record.file_data)

                    mime_type = record.file_type
                    if mime_type == "application/pdf":
                        _logger.info(
                            "Processing record ID %s: Converting data to images.",
                            record.id,
                        )
                        images = convert_from_bytes(data, last_page=40)
                        text = ""

                        _logger.info(
                            "Processing record ID %s: Running OCR on images.", record.id
                        )
                        _logger.info("Processing %s images.", len(images))
                        i = 1
                        for image in images:
                            if i < 10:
                                extracted_text = pytesseract.image_to_string(
                                    image, config=config
                                )
                                text += extracted_text
                                _logger.info("Processing Image %s", i)
                                i = i + 1
                            else:
                                pass

                        record.extracted_text = text
                        _logger.info(
                            "Processing record ID %s: OCR completed successfully.",
                            record.id,
                        )

                    elif mime_type.startswith("image/"):
                        text = ""
                        _logger.info(
                            "Processing record ID %s: Running OCR on image file.",
                            record.id,
                        )
                        image = Image.open(io.BytesIO(data))

                        # Preprocess the image before OCR (if required)

                        # Convert preprocessed image to PIL Image format

                        # Perform OCR on the preprocessed image
                        extracted_text = pytesseract.image_to_string(
                            image, config=config
                        )

                        text += extracted_text

                        record.extracted_text = text

                    elif mime_type == "text/plain":
                        text = ""
                        _logger.info(
                            "Processing record ID %s: Extracting text from text file.",
                            record.id,
                        )
                        extracted_text = data.decode("utf-8")
                        text += extracted_text
                        record.extracted_text = text

                    record.is_ocr_done = True

                except Exception as e:
                    _logger.error(
                        "Processing record ID %s: Failed to OCR the document. Error: %s",
                        record.id,
                        str(e),
                    )
                    record.extracted_text = "Failed to OCR the document"
                    record.is_ocr_done = False

                _logger.info("Completed OCR for all records.")
            else:
                _logger.info(f"OCR already processed for record ID {record.id}.")

            self.action_generate_report()

    def process_document(self):
        for record in self:
            if record.record_report_template:
                prompt = ChatPromptTemplate.from_messages(
                    [
                        SystemMessage(
                            content=prompts.system_global_report(
                                record.record_locale,
                                record.record_report_template[0].template_definition,
                            )
                        ),  # The persistent system prompt
                        MessagesPlaceholder(
                            variable_name="chat_history"
                        ),  # Where the memory will be stored.
                        HumanMessagePromptTemplate.from_template(
                            "{human_input}"
                        ),  # Where the human input will injected
                    ]
                )

                memory = ConversationBufferMemory(
                    memory_key="chat_history", return_messages=True
                )
                llm = AzureLLM()
                chat_llm_chain = LLMChain(
                    llm=llm,
                    prompt=prompt,
                    verbose=False,
                    memory=memory,
                )

                record.description = chat_llm_chain.predict(
                    human_input=prompts.user_html_prompt(record.extracted_text)
                )

            else:
                _logger.error(
                    f"Record ID {record.id}: No record report template found."
                )

    def get_template_data(self, record):
        try:
            template = record.report_template[0]
            sections = template.template_definition or (
                "1. Patient Info\n"
                "2. Medical History\n"
                "3. Diagnosis\n"
                "4. Current Treatments\n"
                "5. Recommendations\n"
                "6. Summary\n"
            )
            footer = template.footer or ""
            header = template.header or ""
            logo = template.logo or ""
        except IndexError:
            _logger.warning(
                f"No template found for record ID {record.id}. Using default sections."
            )
            sections = self.get_default_template_data()
        except Exception as e:
            _logger.error(
                f"Failed to fetch template data for record ID {record.id} due to: {e}. Using default sections."
            )
            sections = self.get_default_template_data()
        return sections, footer, header, logo

    def get_default_template_data(self):
        return (
            "1. Patient Info\n"
            "2. Medical History\n"
            "3. Diagnosis\n"
            "4. Current Treatments\n"
            "5. Recommendations\n"
            "6. Summary\n",
        )

    def action_generate_report(self):
        import datetime

        for record in self:
            _logger.info(
                f"Initiating report generation for record ID {record.id} using ChatGPT-3/4."
            )

            if not record.extracted_text or not record.record_locale:
                _logger.warning(
                    f"Missing data in record ID {record.id}. Skipping this record."
                )
                continue

            input_data = f"Target language: {record.record_locale}. OCR TEXT: {record.extracted_text}"
            sections, footer, header, logo = self.get_template_data(record)

            # _logger.info(f"Extracted sections for record ID {record.id}: {sections}")

            try:
                _logger.info(
                    f"Invoking ChatGPT-3/4 for report generation for record ID {record.id}."
                )
                record.generated_report = DocumentAiActions.build_system_prompt(
                    record.report_template[0].prompt_template_id[0],
                    record.report_template[0],
                    input_data,
                    record.record_locale,
                )
                _logger.info(
                    f"Report generated for record ID {record.id}. Converting to PDF."
                )

                pdf_data = VoiceRecordAiActions.text_to_pdf_formatted(
                    record.generated_report, footer=footer, header=header, logo=logo
                )

                _logger.debug(
                    f"PDF generated for record ID {record.id}. Saving to database."
                )
                record.generated_file = pdf_data

                formatted_date = datetime.datetime.now().strftime("%y%m%d")
                sequence_number = (
                    record.env["ir.sequence"].next_by_code(
                        "wrrrit.ai.voice_record.pdf.sequence"
                    )
                    or "0001"
                )
                report_name = f"{record.name}-{formatted_date}-{sequence_number}-{record.record_locale}"
                _logger.debug(f"Generated PDF {report_name}")

                record.env["wrrrit.ai.voice_record.pdf"].create(
                    {
                        "name": report_name,
                        "pdf_report_data": pdf_data,
                        "medical_document_id": record.id,
                    }
                )
            except Exception as e:
                _logger.error(
                    f"Error during report generation for record ID {record.id}: {e}"
                )

    @staticmethod
    def get_first_json_object(json_string):
        import json

        decoder = json.JSONDecoder()
        pos = 0
        json_object = None
        try:
            json_object, pos = decoder.raw_decode(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")

        return json_object

    def extract_metadata(self):
        from datetime import datetime
        import json

        for record in self:
            system = prompts.system_dictionary()
            user = prompts.extract_metadata(record.extracted_text)
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]

            response = VoiceRecordAiActions.execute_openai_chat_completion(messages)

            _logger.info("Completed Data Extraction call :%s", response)
            try:
                # Strip the leading and trailing triple single quotes
                first_bracket_position = response.find("{")
                last_bracket_position = response.rfind("}")

                if first_bracket_position != -1 and last_bracket_position != -1:
                    cleaned_string = response[
                        first_bracket_position : last_bracket_position + 1
                    ]
                else:
                    cleaned_string = ""  # or however you want to handle no match

                _logger.info("Cleaned String: %s", cleaned_string)

                # Parse the cleaned string to a dictionary
                data = json.loads(cleaned_string)
                _logger.info("Cleaned JSON: %s", data)

                record.extracted_metadata = self.generate_meta_report(data)
                name = data.get("First Name", "")
                last_name = data.get("Last Name", "")
                dob_str = data.get("Date of Birth", "")
                metadata = data

                try:
                    dob = (
                        datetime.strptime(dob_str, "%Y-%m-%d")
                        if dob_str
                        else datetime.strptime("1990-01-01", "%Y-%m-%d")
                    )
                except ValueError:
                    dob = datetime.strptime(
                        "1990-01-01", "%Y-%m-%d"
                    )  # Set default date if dob_str is incorrect

                # Create a new data lake entries
                self.env["wrrrit.data_lake.entry"].create_data_lake_entry(
                    name, last_name, dob, data
                )

            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string, JSONDecodeError: {e}")
            except ValueError as e:
                raise ValueError(f"ValueError occurred: {e}")
            except Exception as e:
                raise ValueError(f"An unexpected error occurred: {e}")

    @staticmethod
    def generate_meta_report(json_data):
        try:
            report_text = ""
            for key, value in json_data.items():
                if isinstance(value, dict):
                    sub_report = f"{key}:\n"
                    for sub_key, sub_value in value.items():
                        sub_report += f"  - {sub_key}: {sub_value}\n"
                    report_text += f"{sub_report}\n"
                else:
                    report_text += f"{key}: {value}\n"
            return report_text
        except Exception as e:
            return f"An error occurred while generating the report: {str(e)}"
