import re
from typing import List

from pipeline.registry.models import (
    DatasetRegistryEntry,
    ProgramRegistryEntry,
    UrlRegistryEntry,
)


class RegistryParser:
    """Parses Markdown registry files into registry models."""

    URL_SECTION_MARKER = "# Master URL Registry"

    def _parse_markdown_table(self, section: str) -> List[List[str]]:
        rows = []
        data_started = False

        for line in section.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                if data_started:
                    break
                continue

            cols = [col.strip() for col in stripped.split("|")[1:-1]]
            if not cols:
                continue

            if cols[0] == "ID" or re.fullmatch(r"-+", cols[0]):
                data_started = True
                continue

            rows.append(cols)

        return rows

    def parse_urls(self, markdown_content: str) -> List[UrlRegistryEntry]:
        if self.URL_SECTION_MARKER not in markdown_content:
            raise ValueError(
                "Could not find the Master URL Registry table in the markdown."
            )

        section = markdown_content.split(self.URL_SECTION_MARKER, 1)[1]
        entries = []

        for cols in self._parse_markdown_table(section):
            if len(cols) < 7:
                continue
            entries.append(
                UrlRegistryEntry(
                    id=cols[0],
                    category=cols[1],
                    name=cols[2],
                    url=cols[3],
                    purpose=cols[4],
                    priority=cols[5],
                    status=cols[6],
                )
            )

        if not entries:
            raise ValueError("Parsed 0 URLs from the URL registry table.")
        return entries

    def _extract_section_blocks(self, text: str, header: str) -> str:
        pattern = re.compile(
            rf"(?:###?|)\s*{re.escape(header)}\s*\n```[^\n]*\n(.*?)```",
            re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            return match.group(1).strip()

        pattern_raw = re.compile(
            rf"(?:###?|)\s*{re.escape(header)}\s*\n"
            r"([A-Za-z0-9_:\-/. \n]*?)"
            r"(?=\n(?:#+|[A-Za-z0-9 ]+)\s*\n```|\n## |\Z)",
            re.DOTALL,
        )
        match_raw = pattern_raw.search(text)
        if match_raw:
            return match_raw.group(1).strip()
        return ""

    def _extract_list(self, text: str, header: str) -> List[str]:
        content = self._extract_section_blocks(text, header)
        if not content:
            return []
        return [
            line.strip()
            for line in content.splitlines()
            if line.strip() and line.strip() != "↓"
        ]

    def parse_programs(self, markdown_content: str) -> List[ProgramRegistryEntry]:
        entries = []
        sections = re.split(r"\n## (BLS-PROGRAM-\d+)", markdown_content)

        for index in range(1, len(sections), 2):
            program_id = sections[index].strip()
            content = sections[index + 1]

            name_match = re.search(r"### (.*)", content)
            name = name_match.group(1).strip() if name_match else ""

            entries.append(
                ProgramRegistryEntry(
                    program_id=program_id,
                    name=name,
                    base_url=self._extract_section_blocks(content, "Base URL")
                    or self._extract_section_blocks(content, "Program URL"),
                    release_page=self._extract_section_blocks(
                        content, "Primary Release Page"
                    )
                    or self._extract_section_blocks(content, "Release Page"),
                    release_schedule=self._extract_section_blocks(
                        content, "Release Schedule"
                    ),
                    related_registries=self._extract_list(content, "Related Registries"),
                    primary_content=self._extract_list(content, "Primary Content")
                    or self._extract_list(content, "Outputs")
                    or self._extract_list(content, "Output Types"),
                    expected_output=self._extract_list(content, "Expected Output"),
                    implementation_status=self._extract_section_blocks(
                        content, "Implementation Status"
                    ),
                )
            )

        if not entries:
            raise ValueError("Parsed 0 programs from the PROGRAM registry.")
        return entries

    def parse_datasets(self, markdown_content: str) -> List[DatasetRegistryEntry]:
        entries = []
        sections = re.split(r"\n## (DATASET-\d+)", markdown_content)

        for index in range(1, len(sections), 2):
            header_id = sections[index].strip()
            content = sections[index + 1]

            dataset_id = (
                self._extract_section_blocks(content, "Dataset ID")
                or f"BLS-{header_id}"
            )

            entries.append(
                DatasetRegistryEntry(
                    dataset_name=self._extract_section_blocks(content, "Dataset Name")
                    or self._extract_section_blocks(content, "Dataset"),
                    dataset_id=dataset_id,
                    program_id=self._extract_section_blocks(content, "Program"),
                    collection_methods=self._extract_list(content, "Collection Methods")
                    or self._extract_list(content, "Methods"),
                    load_registries=self._extract_list(content, "Load Registries"),
                    raw_storage=self._extract_section_blocks(content, "Raw Storage"),
                    processed_storage=self._extract_section_blocks(
                        content, "Processed Storage"
                    )
                    or self._extract_section_blocks(content, "Output"),
                    output_files=self._extract_list(content, "Output Files"),
                    pipeline=self._extract_list(content, "Pipeline"),
                    implementation_status=self._extract_section_blocks(
                        content, "Implementation"
                    )
                    or self._extract_section_blocks(content, "Implementation Status"),
                )
            )

        if not entries:
            raise ValueError("Parsed 0 datasets from the DATASET registry.")
        return entries
