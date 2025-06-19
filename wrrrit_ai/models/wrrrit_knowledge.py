# -*- coding: utf-8 -*-
import logging
import os
import tempfile
import warnings

import base64
import langchain
import openai
from langchain.chains import VectorDBQA
from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from datetime import datetime

from .azur_llm_pool import AzurePoolLLM
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma

warnings.simplefilter("ignore")

_logger = logging.getLogger(__name__)

from odoo import api, fields, models

persist_directory = "db2"
wrrri_llm = AzurePoolLLM(stream=False)


class WrrritKnowledgeDocument(models.Model):
    _name = "wrrrit.ai.knowledge.document"
    _description = "Knowledge document"

    name = fields.Char("Document Name", required=True)
    pdf_knowledge_data = fields.Binary("File Data", inverse="_set_name_from_filename")
    filename = fields.Char("File Name")  # Storing the original filename
    question = fields.Char("Question")
    response = fields.Char("Response")
    embedded = fields.Boolean("Embedded")

    is_user_admin = fields.Boolean(
        compute="_compute_is_user_admin", search="_search_is_user_admin"
    )

    @api.depends()
    def _compute_is_user_admin(self):
        for record in self:
            record.is_user_admin = self.env.user.has_group("base.group_system")

    def _search_is_user_admin(self, operator, value):
        if operator == "=" and value:
            return [("create_uid", "=", self.env.user.id)]
        return []

    @api.onchange("pdf_knowledge_data")
    def _onchange_pdf_knowledge_data(self):
        for record in self:
            if record.filename and not record.name:
                record.name = record.filename

    def _set_name_from_filename(self):
        for record in self:
            if record.filename and not record.name:
                record.name = record.filename

    def embed_knowledge(self):
        _logger.info("Embedding knowledge...")
        os.environ["OPENAI_API_BASE"] = "https://api.openai.com/v1"  # https://example.openai.azure.com/
        

        embedding = OpenAIEmbeddings()
        _logger.info("Embedding knowledge...")

        # Check if the document is already embedded
        if self.embedded:
            # Add logic to perform only QA
            # For now, I'm just using a placeholder. You can expand on this based on your actual QA logic.
            _logger.info("Document is already embedded, performing only QA...")
            vectordb2 = Chroma(
                persist_directory=persist_directory, embedding_function=embedding
            )
            qa = VectorDBQA.from_chain_type(
                llm=wrrri_llm.get_next_llm_instance(),
                chain_type="stuff",
                vectorstore=vectordb2,
            )

            query = self.question
            res = qa.run(query)
            self.response = res
            matching_docs = vectordb2.similarity_search(query)
            _logger.info("Results: %s" % res)
            _logger.info("Matching documents: %s" % matching_docs)

            # Print the type of matching_docs
            _logger.info(f"Type of matching_docs: {type(matching_docs)}")

            for i, doc in enumerate(matching_docs):
                title = doc.metadata.get("document_name", "N/A")
                author = doc.metadata.get("document_id", "N/A")

                _logger.info(f"Document {i+1}:")
                _logger.info(f"Title: {title}")
                _logger.info(f"Author: {author}")

            _logger.info("Response :%s", res)

            return

        document_name = self.name
        document_id = self.id

        pdf_knowledge_data = self.pdf_knowledge_data
        decoded_data = base64.b64decode(pdf_knowledge_data)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", prefix="temp_pdf_"
        ) as temp:
            temp.write(decoded_data)

            temp.flush()
            temp.close()
            temp_filepath = temp.name

        # Now, use the temp_filepath in your loader
        _logger.info("Loading file...:%s" % temp_filepath)

        pdf_loader = (langchain.document_loaders.PDFMinerLoader(temp_filepath))
        documents = pdf_loader.load()
        for document in documents:
            if not hasattr(document, "metadata") or document.metadata is None:
                document.metadata = {}

            # Add document_name and document_id to the metadata of each document
            document.metadata["document_name"] = document_name
            document.metadata["document_id"] = document_id

        _logger.info("File loaded...%s", documents)
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        docs = text_splitter.split_documents(documents)

        _logger.info("Documents split...")

        # Embed and store the texts
        # Supplying a persist_directory will store the embeddings on disk
        for doc in docs:
            doc.metadata["document_name"] = document_name
            doc.metadata["document_id"] = document_id
            doc.metadata["created_by"] = "Wrrrit"

        vectordb = Chroma.from_documents(
            documents=docs, embedding=embedding, persist_directory=persist_directory
        )

        # Set the embedded flag to True after successful embedding
        self.embedded = True


class ChatWithKnowledge(models.Model):
    _name = "wrrrit.chat.knowledge"
    _description = "Chat with Knowledge Base"

    name = fields.Char("Subject", required=True)
    owner_id = fields.Many2one(
        "res.users", string="User", required=True, default=lambda self: self.env.user
    )
    message_ids = fields.One2many(
        "wrrrit.chat.message", "chat_id", string="Messages", ondelete="cascade"
    )
    new_message_content = fields.Text("New Message Content")

    def unlink(self):
        _logger.info("Unlinking messages from chat...")
        # Delete all related messages before deleting the chat record
        for record in self:
            record.message_ids.unlink()
        return super(ChatWithKnowledge, self).unlink()

    def action_submit_message(self):
        def format_content(content, chars_per_line=100):
            # Split the content into lines of up to chars_per_line characters each
            return "\n".join(
                [
                    content[i : i + chars_per_line]
                    for i in range(0, len(content), chars_per_line)
                ]
            )

        for record in self:
            if record.new_message_content:
                # Create a new message with the user's content
                user_message_vals = {
                    "chat_id": record.id,
                    "author": "user",
                    "content": record.new_message_content,
                    "timestamp": fields.Datetime.now(),
                }
                record.message_ids.create(user_message_vals)

                # Get a response from OpenAI
                # Assuming OpenAIEmbeddings, Chroma, VectorDBQA, and OpenAI() are correctly defined and imported
                embedding = OpenAIEmbeddings()
                vectordb = Chroma(
                    persist_directory=persist_directory, embedding_function=embedding
                )
                qa = VectorDBQA.from_chain_type(
                    llm=wrrri_llm.get_next_llm_instance(),
                    chain_type="stuff",
                    vectorstore=vectordb,
                )
                query = record.new_message_content + "(in at least 600 words)"
                response = qa.run(query)

                matching_docs = vectordb.similarity_search(query)
                _logger.info("Results: %s" % response)
                _logger.info("Matching documents: %s" % matching_docs)

                # Append the content of the top 3 matching documents to the response
                for i, doc in enumerate(matching_docs[:3]):
                    title = doc.metadata.get("name")
                    _logger.info("doc metadata: %s", doc.metadata)
                    content = doc.page_content
                    formatted_content = format_content(content)  # Format the content

                    # response += f"\n\nDocument {i+1}:\nTitle: {title}\nContent:\n{formatted_content}"

                _logger.info("Response :%s", response)

                # Create a new message with the system's response
                system_message_vals = {
                    "chat_id": record.id,
                    "author": "system_agent",
                    "content": response,  # Updated response with document content
                    "timestamp": fields.Datetime.now(),
                }
                record.message_ids.create(system_message_vals)

                # Clear the new_message_content field
                record.new_message_content = False


class Message(models.Model):
    _name = "wrrrit.chat.message"
    _description = "Chat Message"

    chat_id = fields.Many2one(
        "wrrrit.chat.knowledge", string="Messages", required=True, ondelete="cascade"
    )
    author = fields.Selection(
        [("user", "User"), ("system_agent", "System Agent")],
        string="Author",
        required=True,
    )
    content = fields.Text("Content", required=True)
    timestamp = fields.Datetime("Timestamp", default=fields.Datetime.now)
    is_user = fields.Boolean(compute="_compute_author_type")
    is_system_agent = fields.Boolean(compute="_compute_author_type")
    relative_timestamp = fields.Char(
        string="Relative Timestamp", compute="_compute_relative_timestamp"
    )

    @api.depends("author")
    def _compute_author_type(self):
        for record in self:
            record.is_user = record.author == "user"
            record.is_system_agent = record.author == "system_agent"

    @api.depends("timestamp")
    def _compute_relative_timestamp(self):
        for record in self:
            now = fields.Datetime.context_timestamp(record, datetime.now())
            timestamp = fields.Datetime.context_timestamp(record, record.timestamp)
            time_diff = now - timestamp
            days, remainder = divmod(time_diff.seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60
            time_parts = []
            if days > 0:
                time_parts.append(f"{days}d")
            if hours > 0:
                time_parts.append(f"{hours}h")
            if minutes > 0:
                time_parts.append(f"{minutes}mn")
            record.relative_timestamp = (
                f'{" ".join(time_parts)} ago' if time_parts else "just now"
            )
