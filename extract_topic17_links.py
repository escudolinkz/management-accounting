import subprocess
import json
import re
import time
from pathlib import Path

THREADS_URL_RE = re.compile(
    r"https?://(?:www\.)?threads\.com/"
    r"(?:@[A-Za-z0-9_.-]+/post/[A-Za-z0-9_-]+|share/[A-Za-z0-9_-]+)"
)


def normalize_threads_url(raw_url):
    match = THREADS_URL_RE.match(raw_url.strip())
    return match.group(0) if match else None


def run_js(js_code):
    escaped_js = js_code.replace('\\', '\\\\').replace('"', '\\"')
    applescript = f'''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "web.telegram.org/a/#-1003921753596_17" then
                    return execute t javascript "{escaped_js}"
                end if
            end repeat
        end repeat
    end tell
    '''
    res = subprocess.check_output(["osascript", "-e", applescript]).decode("utf-8")
    return res

print("Checking MessageList status...")
init_info = json.loads(run_js("""
(() => {
    const list = document.querySelector(".MessageList");
    if (!list) return JSON.stringify({ error: "no list" });
    return JSON.stringify({
        scrollHeight: list.scrollHeight,
        clientHeight: list.clientHeight,
        scrollTop: list.scrollTop
    });
})()
"""))

print("Initial status:", init_info)

# Scroll to top first
print("Scrolling to top of chat...")
run_js("""
(() => {
    const list = document.querySelector(".MessageList");
    if (list) list.scrollTop = 0;
})()
""")
time.sleep(2)

# Verify top state
top_info = json.loads(run_js("""
(() => {
    const list = document.querySelector(".MessageList");
    return JSON.stringify({
        scrollHeight: list.scrollHeight,
        clientHeight: list.clientHeight,
        scrollTop: list.scrollTop
    });
})()
"""))
print("At top:", top_info)

# Extraction loop
all_messages = {}
seen_links = set()
all_unique_links = []

step = 800
current_scroll = 0
max_scroll = top_info.get("scrollHeight", 30000)
stagnant_count = 0
last_msg_count = 0

print(f"Starting traversal across scrollHeight ~{max_scroll}px...")

while current_scroll <= max_scroll + 2000:
    extract_js = f"""
    (() => {{
        const list = document.querySelector(".MessageList");
        if (!list) return JSON.stringify({{ error: "no list" }});

        list.scrollTop = {current_scroll};

        const messages = Array.from(list.querySelectorAll(".Message"));
        const extracted = [];

        for (const m of messages) {{
            const id = m.id;
            const textEl = m.querySelector(".text-content");
            const fullText = textEl ? textEl.innerText : (m.innerText || "");

            const anchorLinks = Array.from(m.querySelectorAll(".text-content a, a.text-entity-link"))
                .map(a => a.href || a.getAttribute("href"))
                .filter(h => h && (h.startsWith("http://") || h.startsWith("https://")));

            const urlRegex = /(https?:\\/\\/[^\\s\\n\\r]+)/g;
            const textLinks = (fullText.match(urlRegex) || []).map(u => u.trim());

            const links = Array.from(new Set([...anchorLinks, ...textLinks]));

            extracted.push({{
                id: id,
                fullText: fullText,
                links: links
            }});
        }}

        return JSON.stringify({{
            currentScroll: list.scrollTop,
            scrollHeight: list.scrollHeight,
            messages: extracted
        }});
    }})()
    """

    try:
        raw_res = run_js(extract_js)
        batch = json.loads(raw_res)
    except Exception as e:
        print(f"Error at scroll {current_scroll}: {e}")
        current_scroll += step
        time.sleep(0.5)
        continue

    batch_msgs = batch.get("messages", [])
    max_scroll = batch.get("scrollHeight", max_scroll)

    for m in batch_msgs:
        mid = m["id"]
        normalized_links = []
        for raw_url in m["links"]:
            url = normalize_threads_url(raw_url)
            if url and url not in normalized_links:
                normalized_links.append(url)
        m["links"] = normalized_links

        if mid not in all_messages:
            all_messages[mid] = m
            for url in normalized_links:
                if url not in seen_links:
                    seen_links.add(url)
                    all_unique_links.append(url)
        else:
            # Merge links if more were rendered
            existing_links = set(all_messages[mid]["links"])
            for url in normalized_links:
                if url not in existing_links:
                    all_messages[mid]["links"].append(url)
                    existing_links.add(url)
                if url not in seen_links:
                    seen_links.add(url)
                    all_unique_links.append(url)

    print(f"Scroll: {current_scroll}/{max_scroll}px | Messages tracked: {len(all_messages)} | Unique links: {len(all_unique_links)}")

    current_scroll += step
    time.sleep(0.6)

print(f"\nFinal tally: {len(all_messages)} messages tracked, {len(all_unique_links)} unique links.")

output_dir = Path(__file__).resolve().parent
output_file = output_dir / "telegram_10k_kontest_links.json"
output_txt = output_dir / "telegram_10k_kontest_links.txt"

result_data = {
    "topic_url": "https://web.telegram.org/a/#-1003921753596_17",
    "topic_name": "HERO Lab Fighter › Kontest Bulanan 10K View Club",
    "total_messages": len(all_messages),
    "total_unique_urls": len(all_unique_links),
    "records": list(all_messages.values())
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result_data, f, indent=2, ensure_ascii=False)

with open(output_txt, "w", encoding="utf-8") as f:
    for u in all_unique_links:
        f.write(u + "\n")

print(f"Saved JSON to: {output_file}")
print(f"Saved TXT to: {output_txt}")
