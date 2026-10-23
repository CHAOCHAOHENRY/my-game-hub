# -*- coding: utf-8 -*-
"""
回归验证脚本 v5：
1. 源码级断言（index.html + server.py 关键修改点）
2. 服务端功能测试（重复名字清理、SSE 断线后 8 秒彻底删除）
"""
import json, os, re, sys, threading, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ERRORS = []

def ok(msg): print("OK", msg)
def fail(msg):
    print("FAIL", msg)
    ERRORS.append(msg)

def assert_re(name, pat, text):
    if re.search(pat, text):
        ok(name)
    else:
        fail(f"{name}: pattern {pat!r} not found")

html = open(os.path.join(BASE, "index.html"), "r", encoding="utf-8").read()
py = open(os.path.join(BASE, "server.py"), "r", encoding="utf-8").read()

# ---------- A. index.html 源码断言 ----------
assert_re("A1 feed 定位改为 bottom", r"#feed\s*\{[^}]*bottom\s*:\s*8px", html)
assert_re("A2 .seat-status CSS 存在", r"\.seat-status\s*\{", html)
assert_re("A3 onlineMap 变量声明", r"var\s+onlineMap\s*=", html)
assert_re("A4 renderSeat 含 seat-status", r"seat-status", html)
assert_re("A5 renderSeat 使用 onlineMap", r"onlineMap\[uid\]===false", html)
assert_re("A6 handleMsg players 更新 onlineMap", r"m\.t==='players'[\s\S]*?onlineMap", html)
assert_re("A7 handleMsg out 更新 onlineMap", r"m\.t==='out'[\s\S]*?onlineMap", html)
assert_re("A8 handleMsg start 初始化 onlineMap", r"m\.t==='start'[\s\S]*?onlineMap", html)
assert_re("A9 shouldEnd landlord 分支", r"g\.role==='landlord'", html)
assert_re("A10 shouldEnd hidden 分支", r"g\.role==='hidden'", html)
assert_re("A11 shouldEnd team 分支", r"g\.role==='team'", html)
assert_re("A12 teamTag landlord 徽章", r"'地主'", html)
assert_re("A13 doIdentity 防御校验", r"seat\s*!==\s*G\.holderSeat", html)

# ---------- B. server.py 源码断言 ----------
assert_re("B1 pending_removals 全局", r"pending_removals\s*=\s*\{}", py)
assert_re("B2 schedule_remove 函数", r"def\s+schedule_remove", py)
assert_re("B3 cancel_remove 函数", r"def\s+cancel_remove", py)
assert_re("B4 SSE 重连取消删除", r"cancel_remove\(uid\)", py)
assert_re("B5 SSE 无效 uid 返回 400", r'self\.send_error\(400,\s*"invalid id"\)', py)
assert_re("B6 finally 调度删除", r"schedule_remove\(uid\)", py)
assert_re("B7 join 清理 stale 同名离线", r"stale\s*=\s*\[", py)

if ERRORS:
    for e in ERRORS:
        print(e)
    sys.exit(1)

# ---------- C. 服务端功能测试 ----------
sys.path.insert(0, BASE)
import server as srv

# 重置状态
srv.ROOM = {"players": {}, "hostUid": None, "lock": threading.Lock()}
srv.pending_removals = {}

httpd = srv.ThreadedServer(("127.0.0.1", 19999), srv.Handler)
t = threading.Thread(target=httpd.serve_forever)
t.daemon = True
t.start()
time.sleep(0.2)

def post(path, data):
    url = f"http://127.0.0.1:19999{path}"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))

def sse_connect(uid):
    url = f"http://127.0.0.1:19999/api/events?id={urllib.parse.quote(uid)}"
    req = urllib.request.Request(url)
    return urllib.request.urlopen(req, timeout=5)

try:
    # C1 首次加入
    r1 = post("/api/join", {"name": "Alice"})
    uid1 = r1["id"]
    assert r1["hostUid"] == uid1, "C1 hostUid"
    assert len(r1["players"]) == 1, "C1 players count"
    ok("C1 首次加入")

    # C2 同名再次加入（旧记录在线）→ 允许两个同名在线
    r2 = post("/api/join", {"name": "Alice"})
    uid2 = r2["id"]
    assert len(r2["players"]) == 2, f"C2 players count {r2['players']}"
    ok("C2 同名在线可重复加入")

    # C3 主动离开 uid1 → 列表只剩 uid2
    post("/api/leave", {"id": uid1})
    time.sleep(0.2)
    r3 = post("/api/join", {"name": "Bob"})
    names3 = [p["name"] for p in r3["players"]]
    assert names3.count("Alice") == 1, f"C3 leave stale fail: {names3}"
    ok("C3 主动离开后旧记录清除")

    # C4 SSE 断线后延迟删除（约 11 秒：3 秒心跳周期 + 8 秒延迟）
    resp = sse_connect(uid2)
    time.sleep(0.2)
    resp.close()
    time.sleep(12)
    r4 = post("/api/join", {"name": "Carol"})
    names4 = [p["name"] for p in r4["players"]]
    assert names4.count("Alice") == 0, f"C4 SSE drop stale fail: {names4}"
    ok("C4 SSE 断线后记录清除")

    # C5 重连取消删除
    uid_carol = r4["id"]
    resp2 = sse_connect(uid_carol)
    time.sleep(0.2)
    resp2.close()
    time.sleep(2)  # 不到 8 秒
    # 再次重连应取消删除
    resp3 = sse_connect(uid_carol)
    time.sleep(0.2)
    resp3.close()
    time.sleep(12)  # 从第二次 close 开始约 11 秒后应删除
    r5 = post("/api/join", {"name": "Dave"})
    names5 = [p["name"] for p in r5["players"]]
    assert names5.count("Carol") == 0, f"C5 re-cancel fail: {names5}"
    ok("C5 重连取消删除机制正常")

except Exception as e:
    import traceback
    traceback.print_exc()
    fail(f"Server test exception: {e}")
finally:
    httpd.shutdown()
    httpd.server_close()

if ERRORS:
    print("\n验证失败：")
    for e in ERRORS:
        print(" -", e)
    sys.exit(1)
print("\n===== ALL PASSED =====")
