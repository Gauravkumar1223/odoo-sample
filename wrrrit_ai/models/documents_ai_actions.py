import base64
import io
import json
import logging
import mimetypes
import tempfile

import cv2
import openai
import pdfkit
import pytesseract

from pdf2image import convert_from_bytes
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageMorph
import numpy as np

from . import prompts
from .llm import WrrritLLM
from .azur_llm_pool import AzurePoolLLM
from .azure_llm import AzureLLM

_logger = logging.getLogger(__name__)


class DocumentAiActions:
    wrrrit_llm = AzurePoolLLM(stream=False)

    @staticmethod
    def preprocess_image(image):
        # Apply preprocessing techniques to improve image quality
        # Example: Convert to grayscale, resize, denoise, or apply other enhancement techniques
        # gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # resized_image = cv2.resize(gray_image, (0, 0), fx=2, fy=2)  # Example resizing to improve OCR accuracy
        return image

    @staticmethod
    def action_ocr_document(records):
        config = ""
        for record in records:
            if record.file:
                try:
                    _logger.info("Processing record ID %s: Decoding file.", record.id)
                    data = base64.b64decode(record.file)

                    mime_type, _ = mimetypes.guess_type(record.name)
                    if mime_type == "application/pdf":
                        _logger.info(
                            "Processing record ID %s: Converting data to images.",
                            record.id,
                        )
                        images = convert_from_bytes(data, last_page=30)
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

                        record.ocr_data = text
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
                        record.ocr_data = text

                    elif mime_type == "text/plain":
                        text = ""
                        _logger.info(
                            "Processing record ID %s: Extracting text from text file.",
                            record.id,
                        )
                        extracted_text = data.decode("utf-8")
                        text += extracted_text
                        record.ocr_data = text

                except Exception as e:
                    _logger.error(
                        "Processing record ID %s: Failed to OCR the document. Error: %s",
                        record.id,
                        str(e),
                    )
                    record.ocr_data = "Failed to OCR the document"

        _logger.info("Completed OCR for all records.")

    @staticmethod
    def enhance_image_for_ocr(image):
        # Convert to grayscale
        image = image.convert("L")

        # # Binarize the image using thresholding to make it black and white
        # threshold = 120  # Adjust this value as needed
        # image = image.point(lambda p: 255 if p > threshold else 0)
        #
        # # Apply median filter for noise reduction
        # image = image.filter(ImageFilter.MedianFilter(size=3))
        #
        # # Enhance contrast
        # enhancer = ImageEnhance.Contrast(image)
        # image = enhancer.enhance(2)  # Double the contrast

        # Increase resolution
        base_width = image.width
        base_height = image.height
        image = image.resize((base_width * 2, base_height * 2), Image.ANTIALIAS)

        return image

    @staticmethod
    def doc_image_ocr(records):
        try:
            for record in records:
                if record.doc_image:
                    data = base64.b64decode(record.doc_image)
                    _logger.info(
                        "Processing record ID %s: Running OCR on image file.",
                        record.id,
                    )
                    image = Image.open(io.BytesIO(data))

                    # Save the image to a temporary file and process with the OCR API
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".png"
                    ) as temp_file:
                        image.save(temp_file, "PNG")
                        extracted_text = DocumentAiActions.ocr_space_file(
                            temp_file.name
                        )

                    record.image_ocr = extracted_text

        except Exception as e:
            _logger.error(
                "Processing record ID %s: Failed to OCR the document. Error: %s",
                record.id,
                str(e),
            )
            record.ocr_data = "Failed to OCR the document"
        finally:
            _logger.info("Completed OCR for all records.")

    @staticmethod
    def ocr_space_file(
        filename, overlay=False, api_key="K83043521788957", language="eng"
    ):
        import requests, json

        payload = {
            "isOverlayRequired": overlay,
            "apikey": api_key,
            "language": language,
        }
        with open(filename, "rb") as f:
            r = requests.post(
                "https://api.ocr.space/parse/image",
                files={filename: f},
                data=payload,
            )
            response_data = json.loads(r.content.decode())

            _logger.info("Parsed Text %s", response_data)
            # Extract ParsedText
            parsed_text = response_data["ParsedResults"][0]["ParsedText"]

            # Convert to HTML format
            parsed_text_html = parsed_text.replace("\r\n", "<br/>")

        return parsed_text_html

    @staticmethod
    def execute_openai_chat_completion(
        messages, temperature=0, max_tokens=10000, model="gpt-3.5--0613"
    ):
        import time, json, sys, os

        _logger.info(
            "Processing Call to  LLM  To Get Global Report on  with LLM Pool.",
            model,
        )

        wrrrit_llm = AzurePoolLLM()

        response = wrrrit_llm.call_llm(messages, max_tokens=8192)

        return response

    def get_information_from_chatgpt3(self, text):
        system = prompts.system_html_prompt3()
        user = prompts.user_html_prompt(text)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.execute_openai_chat_completion(messages)

    @staticmethod
    def get_global_extract_chatgpt(text, locale="english", sections="None"):
        system = prompts.system_global_report(locale, sections)
        user = prompts.user_html_prompt(text)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return DocumentAiActions.execute_openai_chat_completion(messages)

    def get_id_from_chatgpt3(self, text):
        system = prompts.system_id_prompt("")
        user = prompts.user_id_prompt(text)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.execute_openai_chat_completion(
            messages, temperature=0, max_tokens=500
        )

    @staticmethod
    def text_to_pdf(text):
        import pdfkit
        import base64

        # Convert Markdown text to HTML
        html_content = text

        # Set options for proper encoding
        options = {
            "encoding": "UTF-8",
        }

        # Convert HTML to PDF using pdfkit
        pdf_bytes = pdfkit.from_string(html_content, False, options=options)

        # Convert bytes to base64 encoded bytes for storing in Odoo Binary field
        pdf_b64 = base64.b64encode(pdf_bytes)

        return pdf_b64

    def action_compute_meta(self, record):
        for record in record:
            _logger.info(
                "Processing record ID %s: Extracting data using ChatGPT-3/4.", record.id
            )

            # record.description = self.get_translation_from_chatgpt3(record.ocr_data)
            _logger.info("Processing record ID %s: Processing Started.", record.id)
            input_data = (
                "Ensure that the report is fully Generated in "
                + record.record_locale
                + ".\n Do translations."
                "Here is the Transcript: \n " + record.global_summary
            )
            record.global_extract = self.get_information_from_chatgpt3(input_data)

            _logger.info("Processing record ID %s: Processing Finished.", record.id)

            _logger.info(
                "Processing record ID %s: Converting extracted data to PDF.", record.id
            )
            pdf_data = DocumentAiActions.text_to_pdf(record.global_extract)

            _logger.info(
                "Processing record ID %s: Getting summary using ChatGPT-3.", record.id
            )

            base64_pdf_data = pdf_data

            _logger.info(
                "Processing Vocal record ID %s: Saving the generated PDF to the record.",
                record.id,
            )
            # Save the generated PDF to the record
            record.global_report = base64_pdf_data
        _logger.info("Completed processing of  record.")

    def action_compute_fields(self, record):
        for record in record:
            text = record.ocr_data
            record.computed_fields = self.get_id_from_chatgpt3(text)

    def get_summary_from_chatgpt3(self, text):
        system = prompts.system_dictionary()
        user = prompts.extract_metadata(text)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.execute_openai_chat_completion(messages)

    def action_global_extract(self, record):
        import datetime

        for record in record:
            _logger.info(
                "Processing record ID %s: Extracting  Global data using LLM Enterprise.",
                record.id,
            )

            # record.description = self.get_translation_from_chatgpt3(record.ocr_data)
            _logger.info("Processing record ID %s: Processing Started.", record.id)
            input_data = record.global_summary
            try:
                sections = record.report_template[0].template_definition
            except Exception as e:
                _logger.warn(
                    f"Failed to fetch sections for record ID {record.id} due to: {e}. Using default sections."
                )
                sections = (
                    "1. Patient Info\n"
                    "2. Medical History\n"
                    "3. Diagnosis\n"
                    "4. Current Treatments\n"
                    "5. Recommendations\n"
                    "6. Summary\n"
                )

            record.global_extract = self.get_global_extract_chatgpt(
                input_data, record.record_locale, sections
            )

            _logger.info("Processing record ID %s: Processing Finished.", record.id)

            _logger.info(
                "Processing record ID %s: Converting extracted data to PDF.", record.id
            )
            pdf_data = DocumentAiActions.text_to_pdf(record.global_extract)

            _logger.info(
                "Processing record ID %s: Getting summary using ChatGPT-3.", record.id
            )

            base64_pdf_data = pdf_data

            _logger.info(
                "Processing record ID %s: Saving the generated PDF to the record.",
                record.id,
            )
            # Save the generated PDF to the record
            record.global_report = base64_pdf_data
            formatted_date = datetime.datetime.now().strftime("%y%m%d")
            # Fetch the next sequence number for the reports. This assumes that you've set up a sequence for this purpose.
            sequence_number = (
                record.env["ir.sequence"].next_by_code(
                    "wrrrit.ai.voice_record.pdf.sequence"
                )
                or "0001"
            )
            report_name = f"{record.name}-{formatted_date}-{sequence_number}-{record.record_locale}"
            _logger.debug("Generated Global PDF %s", report_name)
            # Save the generated PDF report to the list of reports
            record.env["wrrrit.ai.voice_record.pdf"].create(
                {
                    "name": report_name,
                    "pdf_report_data": pdf_data,
                    "grouped_voices_record_id": record.id,
                }
            )

        _logger.info("Completed processing of  record.")

    def action_compute_doctor(self, record):
        for record in record:
            _logger.info(
                "Processing record ID %s: Extracting data using ChatGPT-3.", record.id
            )
            text = record.ocr_data
            record.description = self.get_information_from_chatgpt3(text)

        _logger.info("Completed processing of all records.")

    @staticmethod
    def extract_passport_data(text: str):
        """Extracts passport data from a raw unstructured text file.

        Args:
                        text: The raw unstructured text file.

        Returns:
                        A dictionary of the extracted passport data.
        """
        data = {}

        # Helper function to generate completion using Chat API
        def generate_completion(text):
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=text,
                max_tokens=100,
                n=1,
                stop=None,
                temperature=0.0,
            )
            completion_text = response.choices[0].text.strip()
            _logger.info(f"Generated completion: '{completion_text}'")
            return completion_text

        # Extract the passport number.
        prompt = f"Extract the passport number from this text: '{text}'"
        data["passport_number"] = generate_completion(prompt)

        # Extract the birth date.
        prompt = (
            f"Extract the birth date from this text in a formatted date as %Y-%m-%d without comments or prefix: "
            f""
            f""
            f""
            f""
            f""
            f""
            f""
            f""
            f""
            f"'{text}'"
        )
        data["birth_date"] = generate_completion(prompt)

        # Extract the issue date.
        prompt = (
            f"Extract the issue date from this text as a formatted date, as %Y-%m-%d without comment or prefix"
            f": '{text}'"
        )
        data["issue_date"] = generate_completion(prompt)
        prompt = (
            f"Extract the expiring date from this text as a formatted date  as %Y-%m-%d, without comment or "
            f"prefix: '{text}'"
        )
        data["expiring_date"] = generate_completion(prompt)

        # Extract the citizenship.
        prompt = (
            f"Extract the citizenship from this text, as a country name in English, without comments or prefixes: "
            f""
            f""
            f""
            f""
            f""
            f""
            f""
            f""
            f""
            f"'{text}'"
        )
        data["citizenship"] = generate_completion(prompt)

        prompt = f"Extract the First Name from this text: '{text}'"
        data["first_name"] = generate_completion(prompt)

        prompt = f"Extract the last Name from this text: '{text}'"
        data["last_name"] = generate_completion(prompt)

        # Extract the passport tag.
        prompt = f"Extract the passport tag from this text: '{text}'"
        data["passport_tag"] = generate_completion(prompt)
        _logger.info("Retrieved data %s", data)
        return data

    def get_translation_from_chatgpt3(self, text, locale="english"):
        system = prompts.system_translation_prompt2(locale)
        user = prompts.user_translation_prompt(text)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.execute_openai_chat_completion(messages)

    @staticmethod
    def call_openai_api(
        model, messages=None, prompt=None, temperature=0, max_tokens=5000
    ):
        """
        Call OpenAI API for chat or completion models.

        Args:
                model (str): The model to use (e.g., "gpt-4", "text-davinci-003").
                messages (list): A list of message dicts for chat models.
                prompt (str): A string prompt for completion models.
                temperature (float): The temperature to use for the generation.
                max_tokens (int): The maximum number of tokens to generate.

        Returns:
                str: The generated text.
        """
        if messages is not None:  # For chat models
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response["choices"][0]["message"]["content"]

        elif prompt is not None:  # For completion models
            response = openai.Completion.create(
                engine=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].text.strip()

        else:
            raise ValueError("Either messages or prompt must be provided.")

    def action_translate_meta(self, record):
        for record in record:
            record.computed_fields = self.get_translation_from_chatgpt3(
                record.ocr_data, record.record_locale
            )

    @staticmethod
    def build_system_prompt(prompt_template, report_template, text, locale="english"):
        try:
            # Extracting fields from the PromptTemplate
            prompt_prefix = prompt_template.prompt_prefix or ""
            prompt_sections = prompt_template.prompt_sections or ""
            prompt_postfix = prompt_template.prompt_postfix or ""

            # Extracting fields from the ReportTemplate
            header = report_template.header or ""
            footer = report_template.footer or ""
            template_definition = report_template.template_definition or ""

            # Checking if we should include the current date declaration
            date_declaration = ""
            if prompt_template.insert_date:
                from datetime import datetime

                date_declaration = f"Note: Today  Document Date is: {datetime.now().strftime('%Y-%m-%d')}\n"

            # Checking if we should perform locale translation
            locale_declaration = ""
            if prompt_template.insert_locale:
                locale_declaration = (
                    f"Note: Translate non-{locale} inputs to {locale} everywhere.\n"
                )

            # Building the system prompt
            system_prompt = (
                "Generate the response using strictly the following requirements:\n"
                f"{locale_declaration}"
                f"{date_declaration}"
                f"{prompt_prefix}\n"
                f"{prompt_postfix}\n"
                f"Sections: \n\n{prompt_sections}\n"
                f"{template_definition}\n"
            )

            _logger.info("Generating Prompt:%s", system_prompt)
            # Preparing the user prompt
            user_prompt = f"Text: {text}"

            # Creating the messages array for ChatGPT
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            # Generating report
            # Calling ChatGPT
            wrrrit_llm = AzurePoolLLM(
                # model_completion="gpt-3.5-turbo-instruct",
                # api_base="https://9htad0olhosngj-5001.proxy.runpod.net/v1",
                # max_tokens_model=8096,
            )

            response = wrrrit_llm.call_llm(messages, max_tokens=8192)

            return response
            # return "Mucking GPT"
        except Exception as e:
            _logger.error(
                f"An error occurred while building the system prompt or calling ChatGPT: {e}"
            )
            return None  # Returning None or handle the error as needed
