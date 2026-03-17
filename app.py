import os
import re
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(page_title="Decision OS", page_icon="💭", layout="wide")

# -----------------------------
# config
# -----------------------------
notion_token = os.getenv("NOTION_TOKEN")
notes_db_id = os.getenv("NOTES_DB_ID")
decisions_db_id = os.getenv("DECISIONS_DB_ID")
tasks_db_id = os.getenv("TASKS_DB_ID")

required_vars = {
    "NOTION_TOKEN": notion_token,
    "NOTES_DB_ID": notes_db_id,
    "DECISIONS_DB_ID": decisions_db_id,
    "TASKS_DB_ID": tasks_db_id,
}

missing = [k for k, v in required_vars.items() if not v]

headers = {
    "Authorization": f"Bearer {notion_token}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# -----------------------------
# styles
# -----------------------------
st.markdown("""
<style>
.small-muted {
    font-size: 0.95rem;
    opacity: 0.78;
    margin-left: 8px;
}

.item-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 8px;
}

.section-gap {
    margin-top: 0.35rem;
    margin-bottom: 0.75rem;
}

/* subtle gradient + nicer borders for streamlit bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    background:
        linear-gradient(135deg,
            rgba(59,130,246,0.08) 0%,
            rgba(255,255,255,0.02) 35%,
            rgba(16,185,129,0.04) 100%) !important;
    box-shadow: 0 4px 18px rgba(0,0,0,0.12);
}

/* expander styling */
details {
    border-radius: 12px;
}

/* reduce excess top padding in main area a bit */
.block-container {
    padding-top: 1.6rem;
}

.carousel-caption {
    padding-top: 0.45rem;
    text-align: center;
    opacity: 0.8;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# helper functions
# -----------------------------

# query a notion database
def query_database(database_id: str):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=headers, json={})
    response.raise_for_status()
    return response.json().get("results", [])


# extract title text
def extract_plain_text_from_title(prop: dict) -> str:
    if prop.get("title"):
        return "".join(item.get("plain_text", "") for item in prop["title"])
    return ""


# extract rich text
def extract_plain_text_from_rich_text(prop: dict) -> str:
    if prop.get("rich_text"):
        return "".join(item.get("plain_text", "") for item in prop["rich_text"])
    return ""


# extract select value
def extract_select(prop: dict) -> str:
    if prop.get("select"):
        return prop["select"].get("name", "")
    return ""


# extract checkbox value
def extract_checkbox(prop: dict) -> bool:
    return prop.get("checkbox", False)


# extract date value
def extract_date(prop: dict) -> str:
    if prop.get("date"):
        return prop["date"].get("start", "")
    return ""


# format date for display
def safe_iso_to_pretty(date_str: str) -> str:
    if not date_str:
        return "-"
    try:
        return datetime.fromisoformat(date_str).strftime("%d %b %Y")
    except ValueError:
        return date_str


# infer owner from raw text
def extract_owner(text: str) -> str:
    patterns = [
        r"([A-Z][a-z]+)\s+will",
        r"([A-Z][a-z]+)\s+owns",
        r"([A-Z][a-z]+)\s+to\s+check",
        r"owner\s*[:\-]?\s*([A-Z][a-z]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "Unknown"


# infer follow-up task from raw text
def extract_follow_up_task(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    for sentence in sentences:
        lowered = sentence.lower()
        if any(word in lowered for word in ["will", "need", "review", "check", "owns", "next step"]):
            return sentence.strip()
    return "Review and confirm next action."


# infer rationale from raw text
def extract_rationale(text: str) -> str:
    lowered = text.lower()
    if "because" in lowered:
        after = text[lowered.index("because") + len("because"):].strip()
        return after[:180] if after else "Reason mentioned in the note."
    if "reason" in lowered:
        return "Reason mentioned in the note."
    return "Extracted from supporting context in the note."


# infer revisit date from note text
def infer_revisit_date(raw_notes: str, note_date_str: str):
    if not note_date_str:
        return None

    try:
        base_date = datetime.fromisoformat(note_date_str)
    except ValueError:
        return None

    lowered = raw_notes.lower()

    if "revisit in 2 weeks" in lowered:
        return (base_date + timedelta(days=14)).date().isoformat()
    if "revisit after 2 weeks" in lowered:
        return (base_date + timedelta(days=14)).date().isoformat()
    if "2 weeks" in lowered:
        return (base_date + timedelta(days=14)).date().isoformat()
    if "two weeks" in lowered:
        return (base_date + timedelta(days=14)).date().isoformat()
    if "revisit" in lowered:
        return (base_date + timedelta(days=14)).date().isoformat()

    return None


# default due date
def infer_due_date(note_date_str: str):
    if not note_date_str:
        return None

    try:
        base_date = datetime.fromisoformat(note_date_str)
    except ValueError:
        return None

    return (base_date + timedelta(days=3)).date().isoformat()


# tidy sentence text
def clean_sentence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


# convert extracted sentence into a cleaner decision title
def make_decision_title(sentence: str, fallback_title: str = "") -> str:
    if not sentence:
        return fallback_title or "Decision under discussion"

    lowered = sentence.lower()

    if "onboarding" in lowered and ("fewer steps" in lowered or "simplify" in lowered):
        return "Simplify onboarding flow"

    if "remove phone number" in lowered:
        return "Remove phone number requirement"

    if "annual discount" in lowered or "annual plan discount" in lowered:
        return "Launch annual plan discount"

    if "keep email signup" in lowered:
        return "Keep email signup"

    sentence = re.sub(
        r"^(we agreed|the team agreed|team discussed|decision leaning yes for|decision leaning no for|we decided to|decided to)\s+",
        "",
        sentence.strip(),
        flags=re.IGNORECASE
    )

    sentence = sentence.rstrip(".")
    sentence = sentence[:80].strip()

    if not sentence:
        return fallback_title or "Decision under discussion"

    return sentence[0].upper() + sentence[1:]


# create a short summary
def make_summary(raw_notes: str, decision_sentence: str) -> str:
    sentences = [clean_sentence(s) for s in re.split(r'(?<=[.!?])\s+', raw_notes.strip()) if s.strip()]

    if len(sentences) >= 2:
        return f"{sentences[0]} {sentences[1]}"

    if decision_sentence:
        return decision_sentence

    if sentences:
        return sentences[0]

    return "Decision inferred from note."


# extract structured decision data
def extract_decision(raw_notes: str, project: str, title: str, note_date_str: str) -> dict:
    sentences = re.split(r'(?<=[.!?])\s+', raw_notes.strip())
    decision_sentence = ""

    decision_markers = [
        "agreed", "decision", "decided", "keep", "remove",
        "launch", "leaning", "approved", "rejected"
    ]

    for sentence in sentences:
        lowered = sentence.lower()
        if any(marker in lowered for marker in decision_markers):
            decision_sentence = clean_sentence(sentence)
            break

    if not decision_sentence and sentences:
        decision_sentence = clean_sentence(sentences[0])

    owner = extract_owner(raw_notes)
    follow_up_task = extract_follow_up_task(raw_notes)
    rationale = extract_rationale(raw_notes)
    revisit_date = infer_revisit_date(raw_notes, note_date_str)
    due_date = infer_due_date(note_date_str)

    decision_title = make_decision_title(decision_sentence, title)
    summary = make_summary(raw_notes, decision_sentence)

    return {
        "decision": decision_title,
        "summary": summary,
        "rationale": rationale,
        "owner": owner,
        "project": project or "Unknown",
        "decision_date": note_date_str or None,
        "revisit_date": revisit_date,
        "due_date": due_date,
        "confidence": 0.65 if decision_sentence else 0.4,
        "follow_up_task": follow_up_task
    }
    

# create decision page in notion
def create_decision_page(extracted: dict, source_note_title: str):
    url = "https://api.notion.com/v1/pages"

    properties = {
        "Decision": {
            "title": [{"text": {"content": extracted["decision"][:2000]}}]
        },
        "Summary": {
            "rich_text": [{"text": {"content": extracted["summary"][:2000]}}]
        },
        "Rationale": {
            "rich_text": [{"text": {"content": extracted["rationale"][:2000]}}]
        },
        "Status": {"select": {"name": "Proposed"}},
        "Owner": {
            "rich_text": [{"text": {"content": extracted["owner"][:2000]}}]
        },
        "Project": {
            "rich_text": [{"text": {"content": extracted["project"][:2000]}}]
        },
        "Source Note": {
            "rich_text": [{"text": {"content": source_note_title[:2000]}}]
        },
        "Confidence": {"number": float(extracted["confidence"])},
        "Approved?": {"checkbox": False}
    }

    if extracted.get("decision_date"):
        properties["Decision Date"] = {"date": {"start": extracted["decision_date"]}}

    if extracted.get("revisit_date"):
        properties["Revisit Date"] = {"date": {"start": extracted["revisit_date"]}}

    payload = {
        "parent": {"database_id": decisions_db_id},
        "properties": properties
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


# create task page in notion
def create_task_page(extracted: dict):
    url = "https://api.notion.com/v1/pages"

    properties = {
        "Task": {
            "title": [{"text": {"content": extracted["follow_up_task"][:2000]}}]
        },
        "Related Decision": {
            "rich_text": [{"text": {"content": extracted["decision"][:2000]}}]
        },
        "Owner": {
            "rich_text": [{"text": {"content": extracted["owner"][:2000]}}]
        },
        "Priority": {"select": {"name": "Medium"}},
        "Status": {"select": {"name": "Not Started"}},
        "Project": {
            "rich_text": [{"text": {"content": extracted["project"][:2000]}}]
        }
    }

    if extracted.get("due_date"):
        properties["Due Date"] = {"date": {"start": extracted["due_date"]}}

    payload = {
        "parent": {"database_id": tasks_db_id},
        "properties": properties
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


# mark note as processed
def mark_note_processed(page_id: str):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": {"Processed": {"checkbox": True}}}
    response = requests.patch(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


# map note row into app format
def get_note_data(row):
    page_id = row.get("id")
    props = row.get("properties", {})

    return {
        "page_id": page_id,
        "title": extract_plain_text_from_title(props.get("Title", {})),
        "raw_notes": extract_plain_text_from_rich_text(props.get("Raw Notes", {})),
        "project": extract_plain_text_from_rich_text(props.get("Project", {})),
        "date_value": extract_date(props.get("Date", {})),
        "processed": extract_checkbox(props.get("Processed", {})),
    }


# map decision row into app format
def get_decision_data(row):
    props = row.get("properties", {})
    return {
        "decision": extract_plain_text_from_title(props.get("Decision", {})),
        "summary": extract_plain_text_from_rich_text(props.get("Summary", {})),
        "status": extract_select(props.get("Status", {})),
        "owner": extract_plain_text_from_rich_text(props.get("Owner", {})),
        "project": extract_plain_text_from_rich_text(props.get("Project", {})),
        "decision_date": extract_date(props.get("Decision Date", {})),
        "revisit_date": extract_date(props.get("Revisit Date", {})),
    }


# map task row into app format
def get_task_data(row):
    props = row.get("properties", {})
    return {
        "task": extract_plain_text_from_title(props.get("Task", {})),
        "related_decision": extract_plain_text_from_rich_text(props.get("Related Decision", {})),
        "owner": extract_plain_text_from_rich_text(props.get("Owner", {})),
        "priority": extract_select(props.get("Priority", {})),
        "status": extract_select(props.get("Status", {})),
        "project": extract_plain_text_from_rich_text(props.get("Project", {})),
        "due_date": extract_date(props.get("Due Date", {})),
    }


# align task order to decision order
def sort_tasks_to_match_decisions(decisions, tasks):
    decision_order = {
        (d["decision"] or "").strip(): idx
        for idx, d in enumerate(decisions)
    }

    matched_tasks = []
    unmatched_tasks = []

    for task in tasks:
        related = (task["related_decision"] or "").strip()
        if related in decision_order:
            matched_tasks.append((decision_order[related], task))
        else:
            unmatched_tasks.append(task)

    matched_tasks.sort(key=lambda x: x[0])

    unmatched_tasks = sorted(
        unmatched_tasks,
        key=lambda t: (t["due_date"] or "", t["task"] or "")
    )

    return [task for _, task in matched_tasks] + unmatched_tasks


# render a note card
def render_note_card(note: dict):
    note_label = note["title"] or "Untitled"

    with st.container(border=True):
        st.markdown(f"### {note_label}")

        meta_col1, meta_col2, meta_col3 = st.columns(3)
        meta_col1.write(f"**Project:** {note['project'] or '-'}")
        meta_col2.write(f"**Date:** {safe_iso_to_pretty(note['date_value'])}")
        meta_col3.write(f"**Processed:** {'Yes' if note['processed'] else 'No'}")

        st.write(f"**Raw Notes:** {note['raw_notes']}")

        extracted = extract_decision(
            raw_notes=note["raw_notes"],
            project=note["project"],
            title=note["title"],
            note_date_str=note["date_value"]
        )

        with st.expander(f"Preview extracted decision — {note_label}", expanded=False):
            st.json(extracted)

        if note["processed"]:
            st.info("This note has already been processed.")
        else:
            if st.button(
                f"Process {note_label}",
                key=f"process_{note['page_id']}",
                use_container_width=True
            ):
                try:
                    create_decision_page(extracted, note["title"])
                    create_task_page(extracted)
                    mark_note_processed(note["page_id"])
                    st.success("Note processed successfully.")
                    st.rerun()
                except Exception as e:
                    st.error("Failed to process note.")
                    st.code(str(e))


# init carousel state
def init_carousel_state():
    if "decision_index" not in st.session_state:
        st.session_state.decision_index = 0
    if "task_index" not in st.session_state:
        st.session_state.task_index = 0


# keep index within bounds
def clamp_index(index_value, total):
    if total <= 0:
        return 0
    return max(0, min(index_value, total - 1))


# render decision panel
def render_single_decision_card(decisions):
    with st.container(border=True):
        if not decisions:
            st.info("No decisions logged yet.")
            return

        total = len(decisions)
        st.session_state.decision_index = clamp_index(st.session_state.decision_index, total)
        idx = st.session_state.decision_index
        item = decisions[idx]

        st.markdown(
            f"<div class='item-title'>{item['decision'] or 'Untitled Decision'}</div>",
            unsafe_allow_html=True
        )
        st.write(f"**Project:** {item['project'] or '-'}")
        st.write(f"**Owner:** {item['owner'] or '-'}")
        st.write(f"**Status:** {item['status'] or '-'}")
        st.write(f"**Decision Date:** {safe_iso_to_pretty(item['decision_date'])}")
        st.write(f"**Revisit Date:** {safe_iso_to_pretty(item['revisit_date'])}")

        if item["summary"]:
            st.write(f"**Summary:** {item['summary']}")

        nav1, nav2, nav3 = st.columns([1, 1, 1.2])

        with nav1:
            if st.button(
                "⬅ Prev",
                key="decision_prev",
                use_container_width=True,
                disabled=(idx == 0)
            ):
                st.session_state.decision_index -= 1
                st.rerun()

        with nav2:
            if st.button(
                "Next ➡",
                key="decision_next",
                use_container_width=True,
                disabled=(idx >= total - 1)
            ):
                st.session_state.decision_index += 1
                st.rerun()

        with nav3:
            st.markdown(
                f"<div class='carousel-caption'>Showing {idx + 1} of {total}</div>",
                unsafe_allow_html=True
            )


# render task panel
def render_single_task_card(tasks):
    with st.container(border=True):
        if not tasks:
            st.info("No open tasks right now.")
            return

        total = len(tasks)
        st.session_state.task_index = clamp_index(st.session_state.task_index, total)
        idx = st.session_state.task_index
        item = tasks[idx]

        st.markdown(
            f"<div class='item-title'>{item['task'] or 'Untitled Task'}</div>",
            unsafe_allow_html=True
        )
        st.write(f"**Project:** {item['project'] or '-'}")
        st.write(f"**Owner:** {item['owner'] or '-'}")
        st.write(f"**Priority:** {item['priority'] or '-'}")
        st.write(f"**Status:** {item['status'] or '-'}")
        st.write(f"**Due Date:** {safe_iso_to_pretty(item['due_date'])}")

        if item["related_decision"]:
            st.write(f"**Related Decision:** {item['related_decision']}")

        nav1, nav2, nav3 = st.columns([1, 1, 1.2])

        with nav1:
            if st.button(
                "⬅ Prev",
                key="task_prev",
                use_container_width=True,
                disabled=(idx == 0)
            ):
                st.session_state.task_index -= 1
                st.rerun()

        with nav2:
            if st.button(
                "Next ➡",
                key="task_next",
                use_container_width=True,
                disabled=(idx >= total - 1)
            ):
                st.session_state.task_index += 1
                st.rerun()

        with nav3:
            st.markdown(
                f"<div class='carousel-caption'>Showing {idx + 1} of {total}</div>",
                unsafe_allow_html=True
            )


# -----------------------------
# ui
# -----------------------------
init_carousel_state()

header_col1, header_col2 = st.columns([2.3, 7.7])
with header_col1:
    st.markdown("## 💭 Decision OS")
with header_col2:
    st.markdown(
        "<div style='padding-top: 25px;' class='small-muted'>Turn messy team notes into structured decisions and follow-up actions inside Notion.</div>",
        unsafe_allow_html=True
    )

if missing:
    st.error(f"Missing environment variables: {', '.join(missing)}")
    st.stop()

try:
    # fetch all notion data
    notes_raw = query_database(notes_db_id)
    decisions_raw = query_database(decisions_db_id)
    tasks_raw = query_database(tasks_db_id)

    # transform raw rows
    notes = [get_note_data(row) for row in notes_raw]
    decisions = [get_decision_data(row) for row in decisions_raw]
    tasks = [get_task_data(row) for row in tasks_raw]

    # sort notes and decisions
    notes = sorted(notes, key=lambda n: (n["processed"], n["date_value"] or "", n["title"] or ""))
    decisions = sorted(
        decisions,
        key=lambda d: (d["decision_date"] or "", d["decision"] or ""),
        reverse=True
    )

    # keep only open tasks and align order
    open_tasks = [t for t in tasks if t["status"] != "Done"]
    open_tasks = sort_tasks_to_match_decisions(decisions, open_tasks)

    # top-level metrics
    processed_notes_count = sum(1 for n in notes if n["processed"])
    open_tasks_count = len(open_tasks)
    total_decisions_count = len(decisions)

    st.success("Connected to Notion successfully.")

    # top metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Notes", len(notes))
    m2.metric("Processed Notes", processed_notes_count)
    m3.metric("Decisions Logged", total_decisions_count)
    m4.metric("Open Tasks", open_tasks_count)

    st.markdown("---")

    # top two panels
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("### Recent Decisions")
        render_single_decision_card(decisions)

    with right_col:
        st.markdown("### Open Tasks")
        render_single_task_card(open_tasks)

    st.markdown("---")

    # notes inbox
    st.markdown("## Notes Inbox")

    if not notes:
        st.warning("No notes found in Notes Inbox.")
    else:
        unprocessed_notes = [n for n in notes if not n["processed"]]
        processed_notes = [n for n in notes if n["processed"]]

        # pending notes section
        with st.container(border=True):
            st.markdown("### Pending Notes")
            if not unprocessed_notes:
                st.info("No pending notes. Everything is processed.")
            else:
                for note in unprocessed_notes:
                    render_note_card(note)

        st.write("")

        # processed notes section
        with st.container(border=True):
            st.markdown("### Already Processed Notes")
            if not processed_notes:
                st.info("No processed notes yet.")
            else:
                for note in processed_notes[:5]:
                    render_note_card(note)

except requests.exceptions.HTTPError as e:
    st.error("Notion API returned an error.")
    try:
        st.json(e.response.json())
    except Exception:
        st.code(str(e))

except Exception as e:
    st.error("App failed.")
    st.code(str(e))