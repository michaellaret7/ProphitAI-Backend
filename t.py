events_test = [
    {"timestamp": "2026-04-16T09:12:04", "user_id": "u1", "action": "login", "status": "success"},
    {"timestamp": "2026-04-16T09:12:45", "user_id": "u2", "action": "login", "status": "fail"},
    {"timestamp": "2026-04-16T09:13:10", "user_id": "u1", "action": "purchase", "status": "success"},
    {"timestamp": "2026-04-16T09:13:55", "user_id": "u2", "action": "login", "status": "fail"},
    {"timestamp": "2026-04-16T09:14:20", "user_id": "u2", "action": "login", "status": "success"},
    {"timestamp": "2026-04-16T09:15:00", "user_id": "u3", "action": "purchase", "status": "fail"},
    {"timestamp": "2026-04-16T09:16:30", "user_id": "u1", "action": "logout", "status": "success"},
    {"timestamp": "2026-04-16T09:17:10", "user_id": "u2", "action": "purchase", "status": "success"},
]

target_return = {
    "total_events": 8,
    "unique_users": 3,
    "action_counts": {"login": 4, "purchase": 3, "logout": 1},
    "failure_rate": 0.375,           # fraction of events with status == "fail"
    "most_active_user": "u2",        # user with the most events; break ties by user_id ascending
    "users_with_failed_logins": ["u2"],  # sorted list of user_ids who had at least one failed login
}

from collections import Counter

def analyze_events(events):
    if not events:
        return {
            "total_events": 0, "unique_users": 0,
            "action_counts": {}, "failure_rate": 0.0,
            "most_active_user": None, "users_with_failed_logins": [],
        }

    user_counts = Counter(e["user_id"] for e in events)
    action_counts = Counter(e["action"] for e in events)
    fail_count = sum(1 for e in events if e["status"] == "fail")
    failed_login_users = {e["user_id"] for e in events if e["action"] == "login" and e["status"] == "fail"}

    most_active = min(user_counts, key=lambda u: (-user_counts[u], u))

    return {
        "total_events": len(events),
        "unique_users": len(user_counts),
        "action_counts": dict(action_counts),
        "failure_rate": round(fail_count / len(events), 3),
        "most_active_user": most_active,
        "users_with_failed_logins": sorted(failed_login_users),
    }

