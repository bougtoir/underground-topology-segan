# Forensic audit inputs

`originals/` contains the user-supplied canonical ZIP and inline manuscript.
Both files are read-only and checked against `ORIGINALS_MANIFEST.csv`.

`canonical_source/` is an unpacked inspection copy of the ZIP. It is not used
as an executable source tree because the submitted archive omitted scripts and
raw inputs. The merged repository revision supplies those omitted components,
while all comparisons retain the canonical ZIP and DOCX checksums.
