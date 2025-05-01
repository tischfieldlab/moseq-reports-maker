from dataclasses import dataclass, field
import json
import os
from typing import Any, Dict
import zipfile
import pandas as pd


@dataclass
class MSQConfig:
    name: str = field(default="moseq-report", metadata={"doc": "Name of the report"})
    out_dir: str = field(default=os.getcwd(), metadata={"doc": "Output directory for the report"})
    tmp_dir: str = field(default=os.path.join(os.getcwd(), "tmp"), metadata={"doc": "Temporary directory for intermediate files"})
    ext: str = field(default="msq", metadata={"doc": "File extension for the final output file"})


class MSQ:
    def __init__(self, config: MSQConfig):
        self.config = config
        self.manifest: Dict[str, Any] = {}

    @property
    def report_path(self) -> str:
        """Path to the final report file."""
        return os.path.join(self.config.out_dir, f"{self.config.name}.{self.config.ext}")

    @property
    def spool_path(self) -> str:
        return self.config.tmp_dir

    def prepare(self):
        # Prepare the MSQ report generation process
        pass

    def bundle(self):
        self._write_manifest()
        # Finalize the MSQ report generation process
        zipf = zipfile.ZipFile(self.report_path, "w", zipfile.ZIP_DEFLATED)

        for root, _, files in os.walk(self.spool_path):
            for file in files:
                arcname = os.path.join(os.path.relpath(root, self.spool_path), file)
                zipf.write(os.path.join(root, file), arcname=arcname)
        zipf.close()

    def write_dataframe(self, name: str, data: pd.DataFrame):
        # Write the data to a DataFrame
        dest = os.path.join(self.spool_path, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        data.to_json(dest, orient="split")

    def write_unstructured(self, name: str, data: Any):
        # Write unstructured data to a file
        dest = os.path.join(self.spool_path, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            json.dump(data, f, indent=4)

    def _write_manifest(self):
        # Write the manifest file
        manifest_path = os.path.join(self.spool_path, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=4)
