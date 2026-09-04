#!/usr/bin/env python3
"""Wrapper to call alightpro.js from Python."""
import json
import subprocess
import os

JS_DIR = os.path.dirname(os.path.abspath(__file__))

def _run_js(fn, *args):
    args_json = ', '.join(json.dumps(a) for a in args)
    code = f"""
    const m = require('./alightpro.js');
    (async () => {{
        try {{
            const r = await m.{fn}({args_json});
            console.log(JSON.stringify(r));
        }} catch(e) {{
            console.log(JSON.stringify({{ok:false, message:e.message, step:'exception'}}));
        }}
    }})();
    """
    proc = subprocess.run(
        ["node", "-e", code],
        capture_output=True, text=True, cwd=JS_DIR, timeout=60
    )
    if proc.returncode != 0:
        return {"ok": False, "message": proc.stderr[:300], "step": "node_error"}
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return {"ok": False, "message": f"Invalid output: {proc.stdout[:200]}", "step": "json_error"}

def v3_send(email):
    return _run_js("v3Send", email)

def v3_verify(email, link):
    return _run_js("v3Verify", email, link)

def v4_send(email):
    return _run_js("v4Send", email)

def v4_verify(email, link):
    return _run_js("v4Verify", email, link)
