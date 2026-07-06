# Substack Newsletter Search

Search across all 382+ posts from "Anticipating the Unintended" (publicpolicy.substack.com).

## Skills

### `/substack-search <query>` — Find specific posts

```
/substack-search semiconductor export controls China
/substack-search driving norms pandemic Bengaluru
/substack-search PLI scheme manufacturing
/substack-search Tinbergen rule policy instruments
/substack-search movies India policy
```

Shows ranked results with snippets from multiple sections of each post. After results, you can ask to read any post's full text.

### `/substack-ideas <theme>` — Explore book/writing ideas

```
/substack-ideas India through movies
/substack-ideas book ideas
/substack-ideas urban governance Bangalore
/substack-ideas semiconductor geopolitics
```

Clusters posts by theme, identifies recurring arguments, suggests book concepts with chapter outlines.

## Search tips

- Use concept words, not exact phrases ("driving norms" not "wrong-side driving")
- Search stems words: "driving" matches "drive", "drove"
- Try synonyms if first query misses — your writing may use different terms than you remember
- Each ATU edition has multiple unconnected sections; results show snippets from different sections

## Manual sync

```bash
python3 ~/Projects/frameworks/scripts/sync-substack-db.py        # incremental (new posts only)
python3 ~/Projects/frameworks/scripts/sync-substack-db.py --full  # re-fetch everything
```

Auto-sync runs every 2 weeks via launchd (`com.pranay.substack-sync`).

## Database

- Location: `~/.claude/data/substack-atu.db`
- Check count: `sqlite3 ~/.claude/data/substack-atu.db "SELECT count(*) FROM posts"`
- Sync log: `~/.claude/data/substack-sync.log`
