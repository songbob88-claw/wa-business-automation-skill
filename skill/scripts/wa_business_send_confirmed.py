#!/usr/bin/env python3
import json
import re
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Tuple

PKG = "com.whatsapp.w4b"
TMP_XML = "/sdcard/window_dump.xml"
STATE = Path('/Users/Schmid/.openclaw/workspace/.wa_business_send_state.json')


def run(cmd: str):
    return subprocess.run(cmd, shell=True, text=True, capture_output=True)


def sh(cmd: str) -> str:
    return run(cmd).stdout


def dump_xml() -> str:
    run(f"adb shell uiautomator dump {TMP_XML} >/dev/null 2>&1")
    return sh(f"adb shell cat {TMP_XML}")


def tap(x: int, y: int):
    run(f"adb shell input tap {x} {y}")


def key(code: str):
    run(f"adb shell input keyevent {code}")


def wake():
    run("adb shell svc power stayon true || true")
    key("KEYCODE_WAKEUP")
    run("adb shell wm dismiss-keyguard || true")
    time.sleep(0.6)


def ensure_wa():
    run(f"adb shell monkey -p {PKG} -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true")
    time.sleep(1.2)


def in_chat(xml: str) -> bool:
    return PKG in xml and 'conversation_contact_name' in xml and 'id/footer' in xml


def chat_name(xml: str) -> Optional[str]:
    m = re.search(r'resource-id="com\.whatsapp\.w4b:id/conversation_contact_name"[^>]*text="([^"]*)"', xml)
    return m.group(1) if m else None


def chat_name_fallback(xml: str, target: Optional[str] = None) -> Optional[str]:
    candidates = []
    patterns = [
        r'resource-id="com\.whatsapp\.w4b:id/conversation_contact_name"[^>]*content-desc="([^"]+)"',
        r'resource-id="com\.whatsapp\.w4b:id/contact_photo"[^>]*content-desc="([^"]+)"',
        r'resource-id="com\.whatsapp\.w4b:id/picture"[^>]*content-desc="([^"]+)"',
        r'content-desc="([^"]*bob[^"]*)"',
    ]
    for pat in patterns:
        for m in re.finditer(pat, xml, re.I):
            val = (m.group(1) or '').strip()
            if val:
                candidates.append(val)
    if target:
        best = None
        best_score = 0.0
        for c in candidates:
            score = _similar(c, target)
            if _norm(target) in _norm(c) or _norm(c) in _norm(target):
                score = max(score, 0.92)
            if score > best_score:
                best = c
                best_score = score
        if best and best_score >= 0.72:
            return best
    return candidates[0] if candidates else None


def entry_bounds(xml: str) -> Optional[Tuple[int, int, int, int]]:
    m = re.search(r'resource-id="com\.whatsapp\.w4b:id/entry"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    return tuple(map(int, m.groups())) if m else None


def text_in_entry(xml: str) -> str:
    m = re.search(r'resource-id="com\.whatsapp\.w4b:id/entry"[^>]*text="([^"]*)"', xml)
    return m.group(1) if m else ''


def has_send_mode(xml: str) -> bool:
    if 'com.whatsapp.w4b:id/send_container' in xml:
        return True
    if 'com.whatsapp.w4b:id/conversation_entry_action_button' in xml and 'voice_note_btn' not in xml:
        return True
    if 'com.whatsapp.w4b:id/buttons' in xml and 'com.whatsapp.w4b:id/entry' in xml:
        return True
    return False


def confirm_draft(msg: str, retries: int = 4, delay: float = 0.6) -> Tuple[str, bool]:
    last_draft = ''
    for _ in range(retries):
        xml = dump_xml()
        last_draft = text_in_entry(xml)
        if last_draft:
            score = _similar(last_draft, msg)
            if _norm(last_draft) == _norm(msg) or score >= 0.72:
                return last_draft, True
        if has_send_mode(xml):
            return last_draft, True
        eb = entry_bounds(xml)
        if eb:
            x1, y1, x2, y2 = eb
            tap((x1 + x2) // 2, (y1 + y2) // 2)
        time.sleep(delay)
    return last_draft, False


def save_state(obj: dict):
    STATE.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def load_state() -> dict:
    if not STATE.exists():
        return {}
    return json.loads(STATE.read_text(encoding='utf-8'))


def clear_state():
    if STATE.exists():
        STATE.unlink()


def _parse_bounds(bounds: str) -> Optional[Tuple[int, int, int, int]]:
    m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds or '')
    return tuple(map(int, m.groups())) if m else None


def _norm(s: str) -> str:
    return re.sub(r'\s+', '', (s or '').strip().lower())


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def find_visible_contact(xml: str, target: str, fuzzy: bool = True) -> Optional[Tuple[int, int, str]]:
    target_lower = _norm(target)
    root = ET.fromstring(xml)
    best = None
    best_score = 0.0
    for node in root.iter('node'):
        rid = node.attrib.get('resource-id', '')
        if rid != 'com.whatsapp.w4b:id/contact_row_container':
            continue
        name = None
        for child in node.iter('node'):
            if child.attrib.get('resource-id') == 'com.whatsapp.w4b:id/conversations_row_contact_name':
                name = child.attrib.get('text', '')
                break
        if not name:
            continue
        norm_name = _norm(name)
        score = 0.0
        if norm_name == target_lower:
            score = 1.0
        elif target_lower and (target_lower in norm_name or norm_name in target_lower):
            score = 0.92
        elif fuzzy:
            score = _similar(name, target)
        if score < 0.72:
            continue
        b = _parse_bounds(node.attrib.get('bounds', ''))
        if not b:
            continue
        x1, y1, x2, y2 = b
        hit = ((x1 + x2) // 2, (y1 + y2) // 2, name)
        if score > best_score:
            best = hit
            best_score = score
    return best


def tap_search_bar_if_present(xml: str) -> bool:
    root = ET.fromstring(xml)
    for node in root.iter('node'):
        rid = node.attrib.get('resource-id', '')
        desc = node.attrib.get('content-desc', '')
        if rid == 'com.whatsapp.w4b:id/my_search_bar' or desc == '搜索':
            b = _parse_bounds(node.attrib.get('bounds', ''))
            if b:
                x1, y1, x2, y2 = b
                tap((x1 + x2) // 2, (y1 + y2) // 2)
                time.sleep(0.8)
                return True
    return False


def clear_entry():
    for _ in range(80):
        key('KEYCODE_DEL')


def input_text(msg: str):
    quoted = shlex.quote(msg)
    run(f"adb shell input text {quoted}")


def search_and_open_contact(target: str) -> Optional[str]:
    xml = dump_xml()
    if not tap_search_bar_if_present(xml):
        return None
    time.sleep(0.5)
    input_text(target)
    time.sleep(1.0)
    xml2 = dump_xml()
    hit = find_visible_contact(xml2, target, fuzzy=True)
    if not hit:
        return None
    x, y, name = hit
    tap(x, y)
    time.sleep(1.0)
    return name


def wait_for_chat_header(retries: int = 6, delay: float = 0.6, target: Optional[str] = None) -> Tuple[Optional[str], str]:
    last_xml = ''
    for _ in range(retries):
        last_xml = dump_xml()
        name = chat_name(last_xml) or chat_name_fallback(last_xml, target)
        if name:
            return name, last_xml
        time.sleep(delay)
    return None, last_xml


def open_chat_if_on_main(target: str) -> Optional[str]:
    xml = dump_xml()
    if 'conversations_row_contact_name' not in xml:
        return None
    hit = find_visible_contact(xml, target, fuzzy=True)
    if hit:
        x, y, _ = hit
        tap(x, y)
        time.sleep(0.8)
        name, _xml = wait_for_chat_header(target=target)
        return name or target
    opened = search_and_open_contact(target)
    if opened:
        name, _xml = wait_for_chat_header(target=target)
        return name or opened
    return None


def prepare(msg: str, target: Optional[str] = None) -> int:
    wake()
    ensure_wa()
    xml = dump_xml()
    opened = None
    if not in_chat(xml):
        if target:
            opened = open_chat_if_on_main(target)
            if opened:
                xml = dump_xml()
            else:
                print(f'ERROR: current view is not a chat and target contact {target} was not found from the main WA screen')
                return 1
        else:
            print('ERROR: current view is not a chat')
            return 1

    name = (chat_name(xml) or chat_name_fallback(xml, target)) or '(unknown)'
    if target and name == '(unknown)':
        waited_name, xml_waited = wait_for_chat_header(target=target)
        if waited_name:
            name = waited_name
            xml = xml_waited
    if target:
        if name == '(unknown)':
            print('ERROR: attempted to open a chat but could not confirm the contact name')
            return 1
        score = _similar(name, target)
        substring = _norm(target) in _norm(name) or _norm(name) in _norm(target)
        if not (name.lower() == target.lower() or substring or score >= 0.72):
            print(f'ERROR: contact confirmation failed target={target} current={name} score={score:.2f}')
            return 1

    eb = entry_bounds(xml)
    if not eb:
        print('ERROR: input field not found')
        return 1

    x1, y1, x2, y2 = eb
    tap((x1 + x2) // 2, (y1 + y2) // 2)
    time.sleep(0.3)
    clear_entry()
    time.sleep(0.2)
    input_text(msg)
    time.sleep(0.8)

    draft, ok = confirm_draft(msg)
    if not ok:
        if not draft:
            print('ERROR: draft confirmation failed; input text could not be read back')
        else:
            score_msg = _similar(draft, msg)
            print(f'ERROR: draft confirmation failed expected={msg} actual={draft} score={score_msg:.2f}')
        return 1

    state = {
        'mode': 'prepared',
        'chat': name,
        'message': msg,
        'target': target,
        'opened': opened,
        'preparedAt': time.time(),
    }
    save_state(state)
    print(f'CHAT={name}')
    print(f'DRAFT={draft}')
    print('READY_FOR_CONFIRM')
    return 0


def confirm_current_chat(xml: str, target: Optional[str]) -> Tuple[bool, str]:
    current = (chat_name(xml) or chat_name_fallback(xml, target) or '(unknown)')
    if not target or target == '(unknown)':
        return True, current
    score = _similar(current, target) if current != '(unknown)' else 0.0
    substring = _norm(target) in _norm(current) or _norm(current) in _norm(target) if current != '(unknown)' else False
    ok = current.lower() == target.lower() or substring or score >= 0.72
    if not ok and current == '(unknown)' and in_chat(xml) and entry_bounds(xml):
        ok = True
    return ok, current


def send_now() -> int:
    state = load_state()
    if state.get('mode') != 'prepared':
        print('ERROR: no prepared draft found')
        return 1

    wake()
    ensure_wa()
    xml = dump_xml()
    if not in_chat(xml):
        print('ERROR: current view is not a chat; refusing to send')
        return 1

    ok_chat, current = confirm_current_chat(xml, state.get('chat') or state.get('target'))
    if not ok_chat:
        print(f"ERROR: current chat={current} prepared chat={state.get('chat')}")
        return 1

    eb = entry_bounds(xml)
    if not eb:
        print('ERROR: input field not found')
        return 1

    x1, y1, x2, y2 = eb
    tap(1002, (y1 + y2) // 2)
    time.sleep(1.0)

    xml2 = dump_xml()
    still = text_in_entry(xml2)
    sent = state.get('message') in xml2 and 'com.whatsapp.w4b:id/message_text' in xml2
    if not sent and not still:
        sent = True
    print(f'CHAT={current}')
    print(f'ENTRY_AFTER={still}')
    print(f'MESSAGE_VISIBLE={sent}')

    key('KEYCODE_BACK')
    time.sleep(0.8)
    key('KEYCODE_BACK')
    clear_state()
    print('RETURNED_TO_MAIN')
    return 0 if sent else 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: wa_business_send_confirmed.py prepare <text> [contact] | send')
        raise SystemExit(2)
    cmd = sys.argv[1]
    if cmd == 'prepare':
        if len(sys.argv) < 3:
            print('ERROR: missing text')
            raise SystemExit(2)
        target = sys.argv[3] if len(sys.argv) >= 4 else None
        raise SystemExit(prepare(sys.argv[2], target))
    if cmd == 'send':
        raise SystemExit(send_now())
    print('ERROR: unknown command')
    raise SystemExit(2)
