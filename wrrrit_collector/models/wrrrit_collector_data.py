import logging

from odoo import models, fields
from odoo import api, fields, models, exceptions
import unidecode
from fuzzywuzzy import fuzz
import hashlib
import json

_logger = logging.getLogger(__name__)


class WrrritCollectorData(models.Model):
    _name = "wrrrit.collector.data"
    _description = "AI Collector Data"

    name = fields.Char(string="Name", required=True)
    value = fields.Integer(string="Value")


class WrrritMetadataEntry(models.Model):
    _name = "wrrrit.metadata.entry"
    _description = "Metadata Entry"

    # Fields
    name = fields.Char(string="Name", required=True, default="Metadata Entry")
    data_lake_entry_id = fields.Many2one(
        "wrrrit.data_lake.entry", ondelete="cascade", required=True
    )
    metadata_json = fields.Text(string="Metadata JSON", required=False)
    meta_data_raw = fields.Text(string="Raw Data")
    timestamp = fields.Datetime(
        string="Timestamp", default=fields.Datetime.now, required=True
    )


class WrrritDataLakeEntry(models.Model):
    _name = "wrrrit.data_lake.entry"
    _description = "Data Lake Entry"

    # Fields
    name = fields.Char(string="Name", required=True, default="Data Feed")
    unique_id = fields.Char(
        string="Unique ID", readonly=False, index=True, required=True
    )
    # metadata_json = fields.Text(string='Metadata JSON', required=False)
    entry_created_on = fields.Datetime(
        string="Entry Created On", default=fields.Datetime.now, readonly=True
    )
    entry_last_modified = fields.Datetime(string="Entry Last Modified", readonly=True)
    is_processed = fields.Boolean(string="Is Processed", default=False)
    # meta_data_raw = fields.Text(string='Raw Data')
    metadata_entry_ids = fields.One2many(
        "wrrrit.metadata.entry", "data_lake_entry_id", string="Metadata Entries"
    )

    def standardize_data(self, name, last_name, dob):
        # Convert names to lowercase and remove any accents
        standardized_name = unidecode.unidecode(name.lower().strip())
        standardized_last_name = unidecode.unidecode(last_name.lower().strip())

        # Standardize DOB format
        standardized_dob = dob and dob.strftime("%Y-%m-%d") or ""

        return standardized_name, standardized_last_name, standardized_dob

    def is_potential_duplicate(self, entry_1, entry_2):
        # Compare names and DOBs using fuzzy matching
        name_similarity = fuzz.ratio(entry_1["name"], entry_2["name"])
        last_name_similarity = fuzz.ratio(entry_1["last_name"], entry_2["last_name"])
        dob_similarity = fuzz.ratio(entry_1["dob"], entry_2["dob"])

        # Define a threshold for considering entries as potential duplicates
        similarity_threshold = 85  # For example, 85% similarity

        return (
            name_similarity >= similarity_threshold
            and last_name_similarity >= similarity_threshold
            and dob_similarity >= similarity_threshold
        )

    @api.model
    def create_data_lake_entry(self, name, last_name, dob, metadata):
        # Standardize data
        (
            standardized_name,
            standardized_last_name,
            standardized_dob,
        ) = self.standardize_data(name, last_name, dob)

        # Generate unique_id
        unique_string = f"{standardized_name}{standardized_last_name}{standardized_dob}"
        unique_id = hashlib.sha256(unique_string.encode()).hexdigest()
        unique_name = unique_id[:7] + "…" + unique_id[-6:]

        meta_entry_name = hashlib.md5(json.dumps(metadata).encode("utf-8")).hexdigest()

        personal_data_keys = [
            "Patient Name",
            "Date of Birth",
            "Address",
            "Contact Number",
            "Emergency Contact",
            "First Name",
            "Last Name",
            "Primary Physician/Dermatologist/Cardiologist"
            # ... any other keys representing personal data
        ]

        # Remove personal data keys from metadata
        for key in personal_data_keys:
            metadata.pop(key, None)
        # Convert metadata to JSON
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        metadata_json_structured = json.loads(metadata_json)
        meta_data_raw = self.generate_meta_report(metadata_json_structured)
        current_time = fields.Datetime.now()

        # Check if a metadata entry with the same hashcode already exists
        existing_meta_entry = self.env["wrrrit.metadata.entry"].search(
            [("name", "=", meta_entry_name)], limit=1
        )
        if existing_meta_entry:
            _logger.info(
                "Metadata entry with the same hashcode already exists, skipping creation of new metadata entry."
            )
            return existing_meta_entry.data_lake_entry_id

        # Search for existing entry with the same unique_id
        existing_entry = self.search([("unique_id", "=", unique_id)], limit=1)
        if existing_entry:
            _logger.info("Found existing entry")
            # Create a new metadata entry associated with the existing data lake entry
            self.env["wrrrit.metadata.entry"].create(
                {
                    "name": meta_entry_name,
                    "data_lake_entry_id": existing_entry.id,
                    "metadata_json": metadata_json,
                    "meta_data_raw": meta_data_raw,
                    "timestamp": current_time,
                }
            )
            existing_entry.write(
                {"entry_last_modified": current_time, "name": unique_name}
            )  # Update the entry_last_modified field
            return existing_entry
        else:
            _logger.info("Creating new entry")
            # Create a new data lake entry
            data_lake_entry = self.create(
                {
                    "name": unique_name,
                    "unique_id": unique_id,
                    "entry_last_modified": current_time,  # Set the entry_last_modified field
                }
            )
            # Create a new metadata entry associated with the new data lake entry
            self.env["wrrrit.metadata.entry"].create(
                {
                    "name": meta_entry_name,
                    "data_lake_entry_id": data_lake_entry.id,
                    "metadata_json": metadata_json,
                    "meta_data_raw": meta_data_raw,
                    "timestamp": current_time,
                }
            )
            return data_lake_entry

    @api.model
    def update_metadata(self, unique_id, new_metadata):
        pass

    @api.model_create_multi
    def create(self, vals_list):
        return super(WrrritDataLakeEntry, self).create(vals_list)

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
