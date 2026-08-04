from app.models.issue import Issue, StatusInfo, UserInfo, SprintRef, LatestComment

STATUS_CATEGORY_MAP = {
    "To Do": "todo",
    "New": "todo",
    "In Progress": "in_progress",
    "Done": "done",
}

STATUS_COLOR_MAP = {
    "blue-gray": "#94a3b8",
    "yellow": "#eab308",
    "green": "#22c55e",
    "medium-gray": "#64748b",
}


def map_issue(raw: dict) -> Issue:
    fields = raw.get("fields", {})

    status_raw = fields.get("status", {})
    status_category_raw = status_raw.get("statusCategory", {})
    category_name = status_category_raw.get("name", "To Do")
    category = STATUS_CATEGORY_MAP.get(category_name, "todo")
    color_name = status_category_raw.get("colorName", "blue-gray")
    color = STATUS_COLOR_MAP.get(color_name, "#94a3b8")

    status = StatusInfo(
        name=status_raw.get("name", "Unknown"),
        category=category,
        color=color,
    )

    assignee_raw = fields.get("assignee")
    assignee = None
    if assignee_raw:
        avatars = assignee_raw.get("avatarUrls", {})
        assignee = UserInfo(
            account_id=assignee_raw.get("accountId", ""),
            display_name=assignee_raw.get("displayName", "Unknown"),
            email=assignee_raw.get("emailAddress", ""),
            avatar_url=avatars.get("32x32", ""),
        )

    reporter_raw = fields.get("reporter")
    reporter = None
    if reporter_raw:
        reporter_avatars = reporter_raw.get("avatarUrls", {})
        reporter = UserInfo(
            account_id=reporter_raw.get("accountId", ""),
            display_name=reporter_raw.get("displayName", "Unknown"),
            email=reporter_raw.get("emailAddress", ""),
            avatar_url=reporter_avatars.get("32x32", ""),
        )

    sprint = None
    sprint_field = fields.get("sprint")
    if sprint_field and isinstance(sprint_field, dict):
        sprint = SprintRef(
            id=sprint_field.get("id", 0),
            name=sprint_field.get("name", ""),
            state=sprint_field.get("state", "active"),
        )

    story_points = fields.get("story_points") or fields.get("customfield_10028")

    latest_comment = None
    comment_field = fields.get("comment")
    if comment_field and isinstance(comment_field, dict):
        comments = comment_field.get("comments", [])
        if comments:
            last = comments[-1]
            body_raw = last.get("body", "")
            if isinstance(body_raw, dict):
                content = body_raw.get("content", [])
                text_parts = []
                for block in content:
                    for item in block.get("content", []):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                body_text = " ".join(text_parts)
            else:
                body_text = str(body_raw)
            latest_comment = LatestComment(
                body=body_text[:200],
                author=last.get("author", {}).get("displayName", "Unknown"),
                created=last.get("created", ""),
            )

    return Issue(
        key=raw.get("key", ""),
        id=str(raw.get("id", "")),
        summary=fields.get("summary", ""),
        status=status,
        assignee=assignee,
        reporter=reporter,
        labels=fields.get("labels", []),
        priority=fields.get("priority", {}).get("name", "Medium") if fields.get("priority") else "Medium",
        issue_type=fields.get("issuetype", {}).get("name", "Task") if fields.get("issuetype") else "Task",
        created=fields.get("created", ""),
        updated=fields.get("updated", ""),
        sprint=sprint,
        story_points=float(story_points) if story_points else None,
        latest_comment=latest_comment,
    )
