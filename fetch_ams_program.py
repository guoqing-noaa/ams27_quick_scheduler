#!/usr/bin/env python3
"""
fetch_ams_program.py

Pulls complete program data from AMS Confex API (Conferences, Sessions, Papers,
Rooms, Dates, Times, Abstracts, Authors) and compiles into a clean, normalized
ams_program.json for the AMS Quick Scheduler.
"""

import argparse
import html
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime

# Common Meteorology / Weather Topics for Pre-computed Tags
TOPIC_RULES = {
    "DataAssimilation": [
        r"\bdata assimilation\b", r"\bradar assimilation\b", r"\bsatellite assimilation\b",
        r"\benkf\b", r"\bensemble kalman\b", r"\bvariational\b", r"\b3dvar\b", r"\b4dvar\b",
        r"\bjedi\b", r"\bda\b(?:\s+system|\s+framework|\s+cycling|\s+technique)",
        r"\bbackground error\b", r"\bobservation operator\b"
    ],
    "NWP_RRFS": [
        r"\brrfs\b", r"\bufs\b", r"\bhrrr\b", r"\bfv3\b", r"\bconvective-allowing\b",
        r"\bconvection-allowing\b", r"\bcam\b(?:\s+ensemble|\s+forecast|\s+model)",
        r"\bnumerical weather prediction\b", r"\bnwp\b", r"\bgfs\b", r"\bwrf\b"
    ],
    "MachineLearning_AI": [
        r"\bmachine learning\b", r"\bdeep learning\b", r"\bneural network\b",
        r"\bartificial intelligence\b", r"\bsurrogate\b", r"\bgraph neural\b",
        r"\bfoundation model\b", r"\btransformer\b", r"\bgenerative\b",
        r"\bphysics-informed\b", r"\bpiml\b", r"\bdiffusion model\b"
    ],
    "Radar_RemoteSensing": [
        r"\bweather radar\b", r"\bphased array\b", r"\bdual-pol\b", r"\bdual-polarization\b",
        r"\breflectivity\b", r"\bdoppler\b", r"\bnexrad\b", r"\blidar\b",
        r"\bgoes\b", r"\bsatellite remote sensing\b"
    ],
    "SevereStorms_Tornado": [
        r"\btornado\b", r"\bhail\b", r"\bsupercell\b", r"\bsevere thunderstorm\b",
        r"\blightning\b", r"\bderecho\b", r"\bmesocyclone\b", r"\bsevere convective\b"
    ],
    "Hydrology_Flooding": [
        r"\bflash flood\b", r"\bheavy precipitation\b", r"\bhydrolog\w+",
        r"\brunoff\b", r"\bstreamflow\b", r"\batmospheric river\b", r"\bqpe\b"
    ],
    "RenewableEnergy": [
        r"\bwind energy\b", r"\bsolar power\b", r"\bphotovoltaic\b", r"\boffshore wind\b",
        r"\bclean energy\b", r"\brenewable energy\b", r"\bgrid integration\b"
    ],
    "FireWeather": [
        r"\bwildfire\b", r"\bfire weather\b", r"\bsmoke\b", r"\bplume\b",
        r"\bfuel moisture\b", r"\bpyrocumul\w+"
    ],
    "HPC_GPU": [
        r"\bgpu\b", r"\bhigh performance computing\b", r"\bhpc\b",
        r"\bparallel computing\b", r"\bcuda\b", r"\bexascale\b"
    ],
    "Ensembles_Probabilistic": [
        r"\bensemble\b", r"\bprobabilistic\b", r"\buncertainty quantification\b",
        r"\bensemble prediction\b", r"\bspread\b"
    ]
}

def clean_html(raw_html: str) -> str:
    """Strip HTML tags and unescape entities."""
    if not raw_html:
        return ""
    # Replace breaks/paragraphs with spaces
    text = re.sub(r"<(?:br|p|/p|div|/div)[^>]*>", " ", raw_html, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalize whitespaces
    return re.sub(r"\s+", " ", text).strip()

def tag_content(title: str, abstract: str) -> list:
    """Assign precomputed topic tags based on regex patterns in title and abstract."""
    combined = f"{title} {abstract}".lower()
    tags = []
    for topic, patterns in TOPIC_RULES.items():
        for pat in patterns:
            if re.search(pat, combined, re.IGNORECASE):
                tags.append(topic)
                break
    return tags

def get_ssl_context():
    """Create a verified or fallback SSL context for urllib."""
    try:
        ctx = ssl.create_default_context()
        return ctx
    except Exception:
        return ssl._create_unverified_context()

def fetch_confex_endpoint(meeting_code: str, endpoint: str, ctx=None):
    """Fetch raw JSON from Confex meetingapi.cgi."""
    if ctx is None:
        ctx = ssl._create_unverified_context()
    
    url = f"https://ams.confex.com/ams/{meeting_code}/meetingapi.cgi/{endpoint}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    })
    
    with urllib.request.urlopen(req, context=ctx, timeout=45) as resp:
        content = resp.read().decode("utf-8")
        return json.loads(content)

def build_program_dataset(meeting_code="107ANNUAL", output_path="ams_program.json"):
    print(f"=== Fetching AMS Program Data for [{meeting_code}] ===")
    ctx = ssl._create_unverified_context()
    
    t0 = time.time()
    
    print("1/5 Fetching Conferences & Symposia (Program)...")
    raw_programs = fetch_confex_endpoint(meeting_code, "Program", ctx)
    print(f"    Loaded {len(raw_programs)} programs in {time.time() - t0:.1f}s")
    
    t1 = time.time()
    print("2/5 Fetching Program Book navigation...")
    raw_book = fetch_confex_endpoint(meeting_code, "ModuleProgramBook", ctx)
    valid_program_urls = set()
    if raw_book and isinstance(raw_book, list) and len(raw_book) > 0:
        valid_program_urls = set(raw_book[0].get("ChildList_Program", []))
    print(f"    Identified {len(valid_program_urls)} active conferences in book.")

    t2 = time.time()
    print("3/5 Fetching all Sessions...")
    raw_sessions = fetch_confex_endpoint(meeting_code, "Session", ctx)
    print(f"    Loaded {len(raw_sessions)} sessions in {time.time() - t2:.1f}s")

    t3 = time.time()
    print("4/5 Fetching Slot & Room locations (SlotData)...")
    raw_slots = fetch_confex_endpoint(meeting_code, "SlotData", ctx)
    print(f"    Loaded {len(raw_slots)} slot records in {time.time() - t3:.1f}s")

    t4 = time.time()
    print("5/5 Fetching all Presentations & Abstracts (Paper)...")
    raw_papers = fetch_confex_endpoint(meeting_code, "Paper", ctx)
    print(f"    Loaded {len(raw_papers)} papers in {time.time() - t4:.1f}s")

    print("\nProcessing and normalizing data...")

    # Build Slot Lookup: Paper/ID -> room & times; Session/ID -> room & times
    paper_slot_map = {}
    session_slot_map = {}

    for slot in raw_slots:
        entry_id = slot.get("Entryid")
        sess_id = slot.get("Session_id")
        room = clean_html(slot.get("Room_Name", ""))
        date = slot.get("Slot_Date", "")
        start_time = slot.get("Slot_StartTime", "")
        end_time = slot.get("Slot_EndTime", "")
        sess_start = slot.get("Slot_SessionStartTime", "")
        sess_end = slot.get("Slot_SessionEndTime", "")
        venue = clean_html(slot.get("Property_Name", ""))

        slot_info = {
            "room": room,
            "venue": venue,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "session_start": sess_start,
            "session_end": sess_end
        }

        if entry_id:
            paper_slot_map[entry_id] = slot_info
        if sess_id:
            session_slot_map[sess_id] = slot_info

    # 1. Normalize Conferences
    conferences = []
    conf_by_id = {}
    for p in raw_programs:
        p_url = p.get("_url", "")
        p_id = p.get("id", "")
        title = clean_html(p.get("Title", ""))
        code = p.get("ProgramCode", "")
        
        # Skip trash or unlisted programs if ProgramBook exists
        if valid_program_urls and p_url not in valid_program_urls:
            # Also keep if code is not TRASH
            if code.upper() in ["TRASH", "WASTE BASKET"]:
                continue

        c_data = {
            "id": p_id,
            "code": code,
            "title": title,
            "nav_title": clean_html(p.get("NavBarTitle", "")),
            "session_ids": [s.replace("Session/", "") for s in p.get("ChildList_Session", [])],
            "paper_ids": [pap.replace("Paper/", "") for pap in p.get("ChildList_Paper", [])]
        }
        conferences.append(c_data)
        conf_by_id[p_id] = c_data

    # Sort conferences alphabetically by title
    conferences.sort(key=lambda c: c["title"])

    # 2. Normalize Sessions
    sessions = {}
    for s in raw_sessions:
        s_id = s.get("id", "")
        if not s_id:
            continue
        
        title = clean_html(s.get("Title", ""))
        p_code = s.get("ProgramCode", "")
        p_title = clean_html(s.get("ProgramTitle", ""))
        
        # Extract conference id from ParentList_ParentEntries
        parents = s.get("ParentList_ParentEntries", [])
        conf_id = ""
        for parent in parents:
            if parent.startswith("Program/"):
                conf_id = parent.replace("Program/", "")
                break
        
        # Room & Slot info
        slot_info = session_slot_map.get(s_id, {})
        sort_time = s.get("SortableTimeString", "") # format: 2027-01-12_08:30:00_10:00:00
        date = slot_info.get("date", "")
        start_time = slot_info.get("start_time", "")
        end_time = slot_info.get("end_time", "")

        if not date and sort_time:
            parts = sort_time.split("_")
            if len(parts) >= 1:
                date = parts[0]
            if len(parts) >= 2 and not start_time:
                start_time = parts[1]
            if len(parts) >= 3 and not end_time:
                end_time = parts[2]

        cochairs = clean_html(s.get("TopDisplay", ""))
        if "Cochairs:" in cochairs:
            cochairs = cochairs.replace("Cochairs:", "").strip()

        paper_ids = [p.replace("Paper/", "") for p in s.get("ChildList_Paper", [])]

        sessions[s_id] = {
            "id": s_id,
            "title": title,
            "session_number": s.get("FinalSessionNumber", "") or s.get("FinalNumber", ""),
            "conference_id": conf_id,
            "conference_code": p_code,
            "conference_title": p_title,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "room": slot_info.get("room", ""),
            "venue": slot_info.get("venue", ""),
            "cochairs": cochairs,
            "good_type": s.get("GoodType", "Session"),
            "paper_ids": paper_ids,
            "withdrawn": bool(s.get("Withdrawn", ""))
        }

    # 3. Normalize Papers
    papers = {}
    for p in raw_papers:
        p_id = p.get("id", "")
        if not p_id:
            continue
        
        title = clean_html(p.get("Title", ""))
        abstract = clean_html(p.get("Abstract", ""))
        paper_num = p.get("FinalPaperNumber", "") or p.get("FinalNumber", "")
        good_type = p.get("GoodType", "Oral")
        presenter = clean_html(p.get("PresentingAuthor", ""))
        authors = clean_html(p.get("TopDisplay", ""))
        withdrawn = bool(p.get("Withdrawn", "") or p.get("WithdrawnFromTechprogram", "0") == "1")

        # Session & Conference linkage
        parents = p.get("ParentList_ParentEntries", [])
        sess_id = ""
        conf_id = ""
        for parent in parents:
            if parent.startswith("Session/"):
                sess_id = parent.replace("Session/", "")
            elif parent.startswith("Program/"):
                conf_id = parent.replace("Program/", "")

        # Slot info
        slot_info = paper_slot_map.get(f"Paper/{p_id}", {})
        sort_time = p.get("SortableTimeString", "") # format: 2027-01-12_08:30:00_08:45:00
        date = slot_info.get("date", "")
        start_time = slot_info.get("start_time", "")
        end_time = slot_info.get("end_time", "")
        room = slot_info.get("room", "")

        if not date and sort_time:
            parts = sort_time.split("_")
            if len(parts) >= 1:
                date = parts[0]
            if len(parts) >= 2 and not start_time:
                start_time = parts[1]
            if len(parts) >= 3 and not end_time:
                end_time = parts[2]

        # Inherit room/date from session if missing on paper
        if sess_id and sess_id in sessions:
            parent_sess = sessions[sess_id]
            if not room:
                room = parent_sess.get("room", "")
            if not date:
                date = parent_sess.get("date", "")

        # Tags
        tags = tag_content(title, abstract)

        papers[p_id] = {
            "id": p_id,
            "title": title,
            "number": paper_num,
            "session_id": sess_id,
            "conference_id": conf_id,
            "type": good_type,
            "presenter": presenter,
            "authors": authors,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "room": room,
            "abstract": abstract,
            "tags": tags,
            "withdrawn": withdrawn
        }

    dataset = {
        "metadata": {
            "meeting_code": meeting_code,
            "meeting_title": f"AMS {meeting_code} Annual Meeting",
            "extracted_at": datetime.utcnow().isoformat() + "Z",
            "total_conferences": len(conferences),
            "total_sessions": len(sessions),
            "total_papers": len(papers),
            "available_tags": list(TOPIC_RULES.keys())
        },
        "conferences": conferences,
        "sessions": sessions,
        "papers": papers
    }

    print(f"\nWriting dataset to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done! Saved {file_size_mb:.2f} MB JSON dataset in {time.time() - t0:.1f}s total.")
    print(f"Summary:")
    print(f"  • Conferences: {len(conferences)}")
    print(f"  • Sessions:    {len(sessions)}")
    print(f"  • Papers:      {len(papers)}")
    print(f"  • Pre-computed Tags: {len(TOPIC_RULES)}")

    return dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and normalize AMS Confex program dataset.")
    parser.add_argument("--meeting", default="107ANNUAL", help="AMS meeting code (default: 107ANNUAL)")
    parser.add_argument("--output", default="ams_program.json", help="Output JSON file path")
    args = parser.parse_args()

    build_program_dataset(meeting_code=args.meeting, output_path=args.output)
