import subprocess
import json
import re
from pathlib import Path

THREADS_URL_RE = re.compile(
    r"https?://(?:www\.)?threads\.com/"
    r"(?:@[A-Za-z0-9_.-]+/post/[A-Za-z0-9_-]+|share/[A-Za-z0-9_-]+)"
)


def normalize_threads_url(raw_url):
    match = THREADS_URL_RE.match(raw_url.strip())
    return match.group(0) if match else None


# JavaScript to execute inside Chrome
js_code = """
(() => {
    const list = document.querySelector(".MessageList");
    if (!list) return JSON.stringify({ error: "MessageList not found" });

    const messages = Array.from(list.querySelectorAll(".Message"));
    const results = [];

    for (const m of messages) {
        const id = m.id;
        const textEl = m.querySelector(".text-content");
        const fullText = textEl ? textEl.innerText : (m.innerText || "");

        // Find links via anchors
        const anchorLinks = Array.from(m.querySelectorAll(".text-content a, a.text-entity-link"))
            .map(a => a.href || a.getAttribute("href"))
            .filter(h => h && (h.startsWith("http://") || h.startsWith("https://")));

        // Find links via regex from text
        const urlRegex = /(https?:\\/\\/[^\\s\\n\\r]+)/g;
        const textLinks = (fullText.match(urlRegex) || []).map(u => u.trim());

        // Combine and deduplicate
        const allMsgLinks = Array.from(new Set([...anchorLinks, ...textLinks]));

        results.push({
            id: id,
            fullText: fullText,
            links: allMsgLinks
        });
    }

    return JSON.stringify(results);
})()
"""

# Write JS to a temp string properly escaped for AppleScript
escaped_js = js_code.replace('\\', '\\\\').replace('"', '\\"')

applescript = f'''
tell application "Google Chrome"
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains "web.telegram.org/a/#-1003921753596_3708" then
                return execute t javascript "{escaped_js}"
            end if
        end repeat
    end repeat
end tell
'''

res = subprocess.check_output(["osascript", "-e", applescript]).decode("utf-8")
data = json.loads(res)

output_dir = Path(__file__).resolve().parent
output_file = output_dir / "telegram_100k_hero_links.json"
output_txt = output_dir / "telegram_100k_hero_links.txt"

extracted_records = []
all_unique_urls = []
seen_urls = set()

for m in data:
    full_text = m.get("fullText", "")
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]
    header = lines[0] if lines else ""

    # Check if there is author/member info
    member_name = ""
    for line in lines[:5]:
        if "@" in line or "100K" in line or "Threadhandle" in line or "Penulis" in line:
            member_name += line + " "
    member_name = member_name.strip()

    cleaned_links = []
    for raw_url in m.get("links", []):
        url = normalize_threads_url(raw_url)
        if url and url not in cleaned_links:
            cleaned_links.append(url)
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_unique_urls.append(url)

    extracted_records.append({
        "message_id": m.get("id"),
        "member_info": member_name,
        "full_text": full_text,
        "links": cleaned_links
    })

result_summary = {
    "topic_url": "https://web.telegram.org/a/#-1003921753596_3708",
    "topic_name": "HERO Lab Fighter › 100K View HERO CLUB",
    "total_messages": len(data),
    "total_unique_urls": len(all_unique_urls),
    "records": extracted_records
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result_summary, f, indent=2, ensure_ascii=False)

with open(output_txt, "w", encoding="utf-8") as f:
    for u in all_unique_urls:
        f.write(u + "\n")

print(f"SUCCESS: Extracted {len(all_unique_urls)} unique links from {len(data)} messages.")
print(f"Saved JSON to: {output_file}")
print(f"Saved TXT to: {output_txt}")
