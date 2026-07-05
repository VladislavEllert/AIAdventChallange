# Chunking Strategy Comparison

## Stats

| Metric | Fixed (800w + 120 overlap) | Structural (by headings) |
|---|---|---|
| Total chunks | 150 | 479 |
| Avg size (words) | 717 | 199 |
| Min size (words) | 4 | 2 |
| Max size (words) | 800 | 800 |
| Split sentences (est.) | 120 | 160 |

## Analysis

**Fixed chunking** produces uniform chunk sizes (good for embedding models trained on fixed-length inputs), but splits mid-section — a heading at chunk boundary loses context.

**Structural chunking** preserves semantic units (one section = one chunk). Sections vary wildly in size — very short (stub sections) or very long (must be sub-chunked). Fewer split sentences.

**Winner for retrieval:** structural — section boundaries are natural semantic units. Fixed is a reliable fallback when markdown structure is absent.

## Example: "Anti-Harassment Policy"

### Fixed (first chunk)
```
--- title: "Anti-Harassment Policy" description: "Everyone at GitLab has a responsibility to prevent and stop harassment. Learn more about our Anti-harassment policy." --- {{% panel header="**This is a Secure Document**" header-bg="orange" %}} Per the stated [Roles & Responsibilities](/handbook/people-group/anti-harassment/#roles--responsibilities), changes to this page must be approved or merged ...
```
section: `Anti-Harassment Policy`

### Structural (first chunk)
```
## Introduction

Everyone at GitLab has a responsibility to prevent and stop harassment. Working remotely means that the majority of our interactions are by video call or written communication, such as email or shared documents. The exceptions to this are team summits, attending conferences together, and local team meetups. No matter the method of communication, it is expected that everyone will c...
```
section: `Introduction`
