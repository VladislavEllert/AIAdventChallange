"""Download GitLab Handbook pages → data/rag/corpus/<slug>.md"""
import urllib.request
import urllib.error
import sys
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent.parent / "data" / "rag" / "corpus"
RAW_BASE = "https://gitlab.com/gitlab-com/content-sites/handbook/-/raw/main/content/handbook"

PAGES = [
    # (slug, path_in_repo, title, url)
    ("values", "values/_index.md", "GitLab Values", "https://handbook.gitlab.com/handbook/values/"),
    ("code-review", "engineering/workflow/code-review.md", "Code Review Guidelines", "https://handbook.gitlab.com/handbook/engineering/workflow/code-review/"),
    ("engineering-index", "engineering/_index.md", "Engineering", "https://handbook.gitlab.com/handbook/engineering/"),
    ("engineering-workflow", "engineering/workflow/_index.md", "Engineering Workflow", "https://handbook.gitlab.com/handbook/engineering/workflow/"),
    ("development", "engineering/development/_index.md", "Development", "https://handbook.gitlab.com/handbook/engineering/development/"),
    ("on-call", "engineering/on-call.md", "On-Call", "https://handbook.gitlab.com/handbook/engineering/on-call/"),
    ("incident-management", "engineering/incident-management.md", "Incident Management", "https://handbook.gitlab.com/handbook/engineering/incident-management/"),
    ("communication", "communication/_index.md", "Communication", "https://handbook.gitlab.com/handbook/communication/"),
    ("leadership", "leadership/_index.md", "Leadership", "https://handbook.gitlab.com/handbook/leadership/"),
    ("hiring", "hiring/_index.md", "Hiring", "https://handbook.gitlab.com/handbook/hiring/"),
    ("time-off", "people-group/time-off-and-absence/_index.md", "Time Off and Absence", "https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/"),
    ("time-off-types", "people-group/time-off-and-absence/time-off-types.md", "Time Off Types", "https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/"),
    ("leave-types", "people-group/time-off-and-absence/leave-types.md", "Leave Types", "https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/leave-types/"),
    ("people-group", "people-group/_index.md", "People Group", "https://handbook.gitlab.com/handbook/people-group/"),
    ("anti-harassment", "people-group/anti-harassment.md", "Anti-Harassment Policy", "https://handbook.gitlab.com/handbook/people-group/anti-harassment/"),
    ("directly-responsible-individuals", "people-group/directly-responsible-individuals.md", "Directly Responsible Individuals", "https://handbook.gitlab.com/handbook/people-group/directly-responsible-individuals/"),
    ("competencies", "people-group/competencies.md", "Competencies", "https://handbook.gitlab.com/handbook/people-group/competencies/"),
    ("security", "security/_index.md", "Security", "https://handbook.gitlab.com/handbook/security/"),
    ("product-development", "product-development/_index.md", "Product Development", "https://handbook.gitlab.com/handbook/product-development/"),
    ("reviewer-values", "engineering/workflow/reviewer-values.md", "Reviewer Values", "https://handbook.gitlab.com/handbook/engineering/workflow/reviewer-values/"),
    ("automation", "engineering/workflow/automation.md", "Automation", "https://handbook.gitlab.com/handbook/engineering/workflow/automation/"),
    ("iteration", "engineering/workflow/iteration.md", "Iteration", "https://handbook.gitlab.com/handbook/engineering/workflow/iteration/"),
    ("performance", "engineering/performance.md", "Engineering Performance", "https://handbook.gitlab.com/handbook/engineering/performance/"),
    ("root-cause-analysis", "engineering/workflow/root-cause-analysis.md", "Root Cause Analysis", "https://handbook.gitlab.com/handbook/engineering/workflow/root-cause-analysis/"),
]


def fetch(slug: str, repo_path: str, title: str, source_url: str) -> bool:
    url = f"{RAW_BASE}/{repo_path}"
    dest = CORPUS_DIR / f"{slug}.md"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            content = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  SKIP {slug}: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  SKIP {slug}: {e}")
        return False

    header = f"<!-- source: {source_url} | title: {title} -->\n\n"
    dest.write_text(header + content, encoding="utf-8")
    words = len(content.split())
    print(f"  OK   {slug}: {words} words")
    return True


def main():
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for slug, path, title, url in PAGES:
        ok += fetch(slug, path, title, url)
    total_words = sum(
        len(f.read_text(encoding="utf-8").split())
        for f in CORPUS_DIR.glob("*.md")
    )
    print(f"\nFetched {ok}/{len(PAGES)} pages | Total words: {total_words:,}")
    if total_words < 7500:
        print("WARNING: corpus < 7500 words, consider adding more pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
