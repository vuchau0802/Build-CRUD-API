# Job card

**What it does (one sentence):** Enriches a scraped book record with a category, a one-sentence summary, and quality flags.

**Input:**
```json
{
  "title": "string, 1-300 characters",
  "description": "string or null, up to 2000 characters",
  "price_gbp": "number",
  "availability_text": "string"
}
```

**Output:**
```json
{
  "category": "one of [fiction, nonfiction, poetry, childrens, other]",
  "summary": "one short sentence describing the book",
  "quality_flags": "array of zero or more from [missing_description, vague_title, price_outlier]",
  "confidence": "0.0-1.0"
}
```

**It must never:**
- Invent a category outside the list
- Return free text outside the defined fields
- Judge the book's literary quality or give an opinion — `quality_flags` describes *data* quality (is the record itself complete/sane), not the book's merit

**When unsure it should:** return category `"other"` with confidence below `0.5`, not guess.

## Checking against the three rules

1. **Closed output** — `category` and `quality_flags` both come from fixed lists written above. ✅
2. **One decision** — one book record in, one enrichment out, no memory of previous calls. ✅
3. **A human could grade it** — given a book's title/description, I can look at the assigned category and summary and say whether it's right. ✅
