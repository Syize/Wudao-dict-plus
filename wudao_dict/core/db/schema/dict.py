"""Domain models for the structured dictionary database.

The model separates lexical identities, dictionary entries, and import
provenance. SQLite schema definitions and persistence operations belong to
repository modules.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class EntryKind(StrEnum):
    """Classify the presentation role of a dictionary entry."""

    HEADWORD = "headword"
    PHRASE = "phrase"


class LookupFormType(StrEnum):
    """Classify how a lookup form identifies a headword."""

    HEADWORD = "headword"
    ALIAS = "alias"
    VARIANT = "variant"
    REDIRECT = "redirect"


class PronunciationAccent(StrEnum):
    """Identify the accent or regional convention of a pronunciation."""

    UK = "uk"
    USA = "usa"
    OTHER = "other"


class EntryLinkType(StrEnum):
    """Classify an outgoing link from an entry to a target headword."""

    PHRASE_OF = "phrase_of"
    REDIRECT_TO = "redirect_to"
    SEE_ALSO = "see_also"
    VARIANT_OF = "variant_of"


@dataclass(slots=True)
class DictionaryEdition:
    """Describe one logical edition of a bilingual dictionary.

    :param name: Publisher or dictionary title.
    :type name: str
    :param source_language: Language of lookup headwords.
    :type source_language: str
    :param target_language: Language of definitions or translations.
    :type target_language: str
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param edition: Edition or release label supplied by the source.
    :type edition: str
    :param license_note: Provenance or licence notice for the edition.
    :type license_note: str
    """

    name: str
    source_language: str
    target_language: str
    id: int | None = None
    edition: str = ""
    license_note: str = ""


@dataclass(slots=True)
class SourceArtifact:
    """Record one imported source file for a dictionary edition.

    :param dictionary_edition_id: Identifier of the containing edition.
    :type dictionary_edition_id: int | None
    :param original_filename: Filename observed during import.
    :type original_filename: str
    :param format: Source container or markup format, such as ``mdx``.
    :type format: str
    :param sha256: SHA-256 digest of the unmodified source file.
    :type sha256: str
    :param imported_at: Import timestamp in the application's chosen format.
    :type imported_at: str
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param parser_name: Name of the parser that read the artifact.
    :type parser_name: str
    :param parser_version: Parser version used for this import.
    :type parser_version: str
    """

    dictionary_edition_id: int | None
    original_filename: str
    format: str
    sha256: str
    imported_at: str
    id: int | None = None
    parser_name: str = ""
    parser_version: str = ""


@dataclass(slots=True)
class SourceRecord:
    """Preserve one raw record extracted from a source artifact.

    :param source_artifact_id: Identifier of the artifact containing the record.
    :type source_artifact_id: int | None
    :param source_key: Source-native key or headword for the raw record.
    :type source_key: str
    :param raw_content: Unmodified record content supplied by the source.
    :type raw_content: str
    :param content_hash: Digest of ``raw_content`` for change detection.
    :type content_hash: str
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param sort_order: Position of the record within its artifact.
    :type sort_order: int
    """

    source_artifact_id: int | None
    source_key: str
    raw_content: str
    content_hash: str
    id: int | None = None
    sort_order: int = 0


@dataclass(slots=True)
class Headword:
    """Represent one stable lexical identity used as a query and link target.

    :param language: Language of the headword text.
    :type language: str
    :param display_text: Preferred spelling displayed to a user.
    :type display_text: str
    :param normalized_text: Canonical form used to identify the headword.
    :type normalized_text: str
    :param id: Persistent identifier, if stored.
    :type id: int | None
    """

    language: str
    display_text: str
    normalized_text: str
    id: int | None = None


@dataclass(slots=True)
class LookupForm:
    """Expose one searchable spelling or redirect for a headword.

    :param headword_id: Identifier of the headword resolved by this form.
    :type headword_id: int | None
    :param text: Form as supplied by the source.
    :type text: str
    :param normalized_text: Normalized form used for lookup.
    :type normalized_text: str
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param form_type: Relationship between this form and its headword.
    :type form_type: LookupFormType
    :param sort_order: Source order among forms for the same headword.
    :type sort_order: int
    """

    headword_id: int | None
    text: str
    normalized_text: str
    id: int | None = None
    form_type: LookupFormType = LookupFormType.HEADWORD
    sort_order: int = 0


@dataclass(slots=True)
class Entry:
    """Represent one dictionary entry under a headword.

    :param headword_id: Identifier of the lexical identity owning the entry.
    :type headword_id: int | None
    :param sort_order: Display order within the headword.
    :type sort_order: int
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param source_record_id: Raw record from which this entry was parsed.
    :type source_record_id: int | None
    :param homograph_label: Source label distinguishing same-spelling entries.
    :type homograph_label: str
    :param entry_kind: Presentation role of the entry.
    :type entry_kind: EntryKind
    """

    headword_id: int | None
    sort_order: int
    id: int | None = None
    source_record_id: int | None = None
    homograph_label: str = ""
    entry_kind: EntryKind = EntryKind.HEADWORD


@dataclass(slots=True)
class Pronunciation:
    """Describe one pronunciation attached to an entry.

    :param entry_id: Identifier of the entry owning the pronunciation.
    :type entry_id: int | None
    :param value: Pronunciation text in the declared notation.
    :type value: str
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param accent: Accent or regional convention of the pronunciation.
    :type accent: PronunciationAccent
    :param notation: Phonetic notation, normally ``ipa``.
    :type notation: str
    :param sort_order: Display order within the entry.
    :type sort_order: int
    """

    entry_id: int | None
    value: str
    id: int | None = None
    accent: PronunciationAccent = PronunciationAccent.OTHER
    notation: str = "ipa"
    sort_order: int = 0


@dataclass(slots=True)
class Sense:
    """Represent one definition or nested sub-definition in an entry.

    :param entry_id: Identifier of the entry owning the sense.
    :type entry_id: int | None
    :param sort_order: Display order within the entry or parent sense.
    :type sort_order: int
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param parent_sense_id: Parent sense when the source has nested meanings.
    :type parent_sense_id: int | None
    :param sense_label: Source-supplied number or label.
    :type sense_label: str
    :param part_of_speech: Grammatical category shown for the sense.
    :type part_of_speech: str
    :param grammar_note: Grammar information attached to the sense.
    :type grammar_note: str
    :param definition: Definition in the source language.
    :type definition: str
    :param translation: Translation in the target language.
    :type translation: str
    :param usage_labels: Register or usage labels.
    :type usage_labels: list[str]
    :param domains: Subject-domain labels.
    :type domains: list[str]
    :param note: Additional source note for the sense.
    :type note: str
    """

    entry_id: int | None
    sort_order: int
    id: int | None = None
    parent_sense_id: int | None = None
    sense_label: str = ""
    part_of_speech: str = ""
    grammar_note: str = ""
    definition: str = ""
    translation: str = ""
    usage_labels: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(slots=True)
class Example:
    """Store one bilingual example attached to a sense.

    :param sense_id: Identifier of the sense illustrated by the example.
    :type sense_id: int | None
    :param source_text: Example text in the source language.
    :type source_text: str
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param target_text: Translation or gloss of the example.
    :type target_text: str
    :param sort_order: Display order within the sense.
    :type sort_order: int
    """

    sense_id: int | None
    source_text: str
    id: int | None = None
    target_text: str = ""
    sort_order: int = 0


@dataclass(slots=True)
class EntryLink:
    """Record an outgoing entry link whose target is a headword.

    ``target_text`` is retained even when target resolution fails, so imports do
    not lose a source reference merely because its target is unavailable.

    :param source_entry_id: Identifier of the entry emitting the link.
    :type source_entry_id: int | None
    :param target_text: Target text as written by the source.
    :type target_text: str
    :param target_normalized_text: Normalized target text used during resolution.
    :type target_normalized_text: str
    :param relation_type: Semantic relation represented by the link.
    :type relation_type: EntryLinkType
    :param id: Persistent identifier, if stored.
    :type id: int | None
    :param target_headword_id: Resolved target headword, when available.
    :type target_headword_id: int | None
    :param sort_order: Source order among links from the same entry.
    :type sort_order: int
    """

    source_entry_id: int | None
    target_text: str
    target_normalized_text: str
    relation_type: EntryLinkType
    id: int | None = None
    target_headword_id: int | None = None
    sort_order: int = 0


@dataclass(slots=True)
class EntryDetail:
    """Aggregate the structured content required to render one entry.

    :param entry: Entry represented by this aggregate.
    :type entry: Entry
    :param pronunciations: Pronunciations attached to the entry.
    :type pronunciations: list[Pronunciation]
    :param senses: Senses belonging to the entry.
    :type senses: list[Sense]
    :param examples: Examples belonging to those senses.
    :type examples: list[Example]
    :param links: Outgoing links emitted by the entry.
    :type links: list[EntryLink]
    """

    entry: Entry
    pronunciations: list[Pronunciation] = field(default_factory=list)
    senses: list[Sense] = field(default_factory=list)
    examples: list[Example] = field(default_factory=list)
    links: list[EntryLink] = field(default_factory=list)


@dataclass(slots=True)
class HeadwordDetail:
    """Aggregate all entries returned for one resolved headword.

    :param headword: Lexical identity resolved by the lookup.
    :type headword: Headword
    :param entries: Ordered entries associated with the headword.
    :type entries: list[EntryDetail]
    :param lookup_forms: Forms that resolve to the headword.
    :type lookup_forms: list[LookupForm]
    """

    headword: Headword
    entries: list[EntryDetail] = field(default_factory=list)
    lookup_forms: list[LookupForm] = field(default_factory=list)


__all__ = [
    "DictionaryEdition",
    "Entry",
    "EntryDetail",
    "EntryKind",
    "EntryLink",
    "EntryLinkType",
    "Example",
    "Headword",
    "HeadwordDetail",
    "LookupForm",
    "LookupFormType",
    "Pronunciation",
    "PronunciationAccent",
    "Sense",
    "SourceArtifact",
    "SourceRecord",
]
