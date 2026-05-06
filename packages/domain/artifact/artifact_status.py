from enum import Enum


class ArtifactType(str, Enum):
    DOC_OUTLINE = "doc_outline"
    DOC_DRAFT = "doc_draft"
    SLIDE_OUTLINE = "slide_outline"
    SLIDE_DECK = "slide_deck"


class ArtifactStatus(str, Enum):
    GENERATED = "GENERATED"
    EDITING = "EDITING"
    APPROVED = "APPROVED"
    REGENERATE_REQUESTED = "REGENERATE_REQUESTED"
    REGENERATING = "REGENERATING"
    PUBLISHED = "PUBLISHED"
