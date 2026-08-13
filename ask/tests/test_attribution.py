from ask.attribution import split_sections, classify_signature


SAMPLE_BODY = """Some intro text nobody signed, not a real section.

India Policy Watch: Regulating Medical Devices

This is the body of the first section. It needs to be long enough to
clear the minimum length filter, so here is some more filler text
about medical device regulation and unintended consequences that a
policy newsletter section would plausibly contain.

—RSJ

Global Policy Watch: A Second Section

This is the body of the second section, also padded out to be long
enough to survive the minimum length filter used by split_sections,
discussing a completely different global policy topic in some detail.

—Pranay Kotasthane

Matsyanyaaya: A Joint Section

This section has no trailing signature line at all, so it should be
attributed to both authors jointly rather than to either one alone,
and it also needs to be padded to clear the length filter.

PolicyWTF: A Guest Section

This section was written by someone outside the two hosts, so even
though it's long enough to pass the length filter, it should be
dropped entirely because the signature doesn't match either alias set.

—Guest Post by Ameya Naik
"""


def test_classify_signature_pranay():
    assert classify_signature("Pranay Kotasthane") == "Pranay"


def test_classify_signature_pranay_typo():
    assert classify_signature("Pranay Kotashane") == "Pranay"


def test_classify_signature_rsj_short():
    assert classify_signature("RSJ") == "RSJ"


def test_classify_signature_rsj_full_name():
    assert classify_signature("Raghu Sanjaylal Jaitley") == "RSJ"


def test_classify_signature_joint_both_present():
    assert classify_signature("RSJ and Pranay Kotasthane") == "Joint"


def test_classify_signature_guest_returns_none():
    assert classify_signature("Guest Post by Ameya Naik") is None


def test_split_sections_extracts_four_headers_drops_guest():
    sections = split_sections(SAMPLE_BODY)
    headers = [s["header"] for s in sections]
    assert headers == ["India Policy Watch", "Global Policy Watch", "Matsyanyaaya"]


def test_split_sections_assigns_correct_authors():
    sections = split_sections(SAMPLE_BODY)
    by_header = {s["header"]: s for s in sections}
    assert by_header["India Policy Watch"]["author"] == "RSJ"
    assert by_header["Global Policy Watch"]["author"] == "Pranay"
    assert by_header["Matsyanyaaya"]["author"] == "Joint"


def test_split_sections_captures_title_and_text():
    sections = split_sections(SAMPLE_BODY)
    first = sections[0]
    assert first["title"] == "Regulating Medical Devices"
    assert "medical device regulation" in first["text"]
    assert first["text"].strip().endswith("—RSJ")


def test_split_sections_drops_short_sections():
    short_body = "Global Policy Watch: Too Short\n\nJust a line.\n\n—RSJ\n"
    assert split_sections(short_body) == []


def test_split_sections_no_headers_returns_empty():
    assert split_sections("Just a plain newsletter intro with no section headers at all.") == []
