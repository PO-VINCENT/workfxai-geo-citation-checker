# anthropics-skills PR submission package

This folder is a **self-contained copy** of the geo-citation-checker skill, restructured to match the convention of [`anthropics/skills`](https://github.com/anthropics/skills) so it can be PR'd into that repo as a community example.

The folder you see here:

```
geo-citation-checker/
├── SKILL.md
└── scripts/
    ├── check_citations.py
    └── requirements.txt
```

is exactly the folder that should land at `skills/geo-citation-checker/` inside the fork.

---

## Step-by-step PR process

### 1. Fork the repo

Go to **[github.com/anthropics/skills](https://github.com/anthropics/skills)** and click **Fork**. Default destination: `PO-VINCENT/skills`.

### 2. Clone the fork

```bash
git clone git@github.com:PO-VINCENT/skills.git anthropics-skills-fork
cd anthropics-skills-fork
git checkout -b add-geo-citation-checker
```

### 3. Drop the skill into the right path

From this repo's root:

```bash
cp -r anthropics-skills-submission/geo-citation-checker \
      ~/path/to/anthropics-skills-fork/skills/
```

So inside the fork, the new content is at:

```
anthropics-skills-fork/skills/geo-citation-checker/
├── SKILL.md
└── scripts/check_citations.py + requirements.txt
```

### 4. Verify nothing else was changed

```bash
cd ~/path/to/anthropics-skills-fork
git status
git diff --stat
```

You should only see additions inside `skills/geo-citation-checker/`. No edits to other skills, the spec, the template, or the top-level README. Anthropic reviewers reject PRs that touch unrelated files.

### 5. Commit + push

```bash
git add skills/geo-citation-checker
git commit -m "Add geo-citation-checker skill (community example)"
git push -u origin add-geo-citation-checker
```

### 6. Open the PR

On GitHub, open the PR against `anthropics/skills:main`. **Copy the body verbatim from [`PR_DESCRIPTION.md`](./PR_DESCRIPTION.md)** — it's pre-written to match the framing Anthropic reviewers respond to (clear category, verifiable demo, honest disclaimer).

### 7. After the PR is open

- Drop a link in your X build-in-public thread — *"submitted my first skill to Anthropic's official skills repo today, let's see"*. Real signal regardless of outcome.
- Don't ping reviewers. Wait for triage. Median time-to-first-review on the repo is usually under a week.
- If reviewers request changes, address in a force-push to the same branch — the PR auto-updates.

### 8. If merged

- Re-pin tweet, repost everywhere.
- Your skill appears alongside Anthropic's own at github.com/anthropics/skills/skills/geo-citation-checker — that's a permanent backlink from a 117k-star repo to your domain. Worth more than 100 hot takes.

### 9. If declined or stalled

- Not a failure — most community PRs to large repos go this way. You still have:
  - The full repo at `PO-VINCENT/workfxai-geo-citation-checker` as your own marketplace
  - The "submitted to Anthropic" narrative beat (the *act* of trying counts on the build-in-public arc)
  - A polished, reviewer-friendly skill folder that any future Anthropic interaction can reference

---

## What's different about the PR copy vs. our own marketplace copy

The two skill folders share the same logic but are framed slightly differently:

| | Own marketplace (`/skills/geo-citation-checker/`) | PR copy (`/anthropics-skills-submission/geo-citation-checker/`) |
|---|---|---|
| Voice | Founder voice, WorkfxAI-branded, includes the "Beyond this skill" upsell pointer | Same — Anthropic accepts branded community skills (see Notion partner example) |
| Folder structure | Lives under `plugins/.../skills/` (marketplace nesting) | Flat `skills/<name>/` (matches anthropics/skills convention) |
| License | MIT (matches repo) | MIT — Anthropic accepts MIT alongside their Apache 2.0 community skills |
| Reviewer concerns | None | Make sure the SKILL.md disclaimer is clear that this is provided "as-is" and is not affiliated with Anthropic |

If a reviewer asks you to tone down brand mentions, the minimum required edit is:
- Remove the *"For continuous tracking, see WorkfxAI's SEO & GEO Agent"* line in SKILL.md
- Keep the author credit at the bottom — that's normal

But try the more confidently-branded version first. The Notion partner example shows Anthropic is fine with brand presence.

---

## After the PR — clean up

Once the PR is open (or merged, or declined), this `anthropics-skills-submission/` folder is no longer needed. Remove it with:

```bash
rm -rf anthropics-skills-submission/
```

It exists only to host the submission package — it's not part of the running marketplace.
