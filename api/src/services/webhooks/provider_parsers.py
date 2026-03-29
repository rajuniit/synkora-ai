"""Parse webhook payloads from different providers."""

import re
from datetime import UTC, datetime
from typing import Any


class ProviderParser:
    """Parse webhook payloads from different providers into a standardized format."""

    # Pattern for extracting @mentions
    # Matches @username where username is 1-39 chars (GitHub limit), alphanumeric with single hyphens
    MENTION_PATTERN = re.compile(r"@([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?)")

    @staticmethod
    def _extract_mentions(text: str | None) -> list[str]:
        """
        Extract @mentions from text.

        Args:
            text: Text to search for mentions

        Returns:
            List of unique usernames mentioned (without @ prefix)
        """
        if not text:
            return []
        matches = ProviderParser.MENTION_PATTERN.findall(text)
        # Return unique mentions, preserving order
        seen = set()
        unique = []
        for m in matches:
            if m.lower() not in seen:
                seen.add(m.lower())
                unique.append(m)
        return unique

    @staticmethod
    def parse_github(payload: dict[str, Any], github_event: str | None = None) -> dict[str, Any]:
        """
        Parse GitHub webhook payload.

        Supported events:
        - pull_request (opened, closed, reopened, synchronize)
        - issues (opened, closed, reopened)
        - push
        - issue_comment
        - pull_request_review
        """
        action = payload.get("action", "")

        # Combine GitHub event type with action for more specific event_type
        # e.g., "pull_request.opened", "issues.closed", "push"
        if github_event and action:
            event_type = f"{github_event}.{action}"
        elif github_event:
            event_type = github_event
        elif action:
            event_type = action
        else:
            event_type = "unknown"

        # Extract common fields
        parsed = {
            "provider": "github",
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "repository": None,
            "sender": None,
            "data": {},
            "mentions": [],  # List of @mentions found in the payload
        }

        # Repository info
        if "repository" in payload:
            repo = payload["repository"]
            parsed["repository"] = {
                "name": repo.get("full_name"),
                "url": repo.get("html_url"),
                "default_branch": repo.get("default_branch"),
            }

        # Sender info
        if "sender" in payload:
            sender = payload["sender"]
            parsed["sender"] = {"username": sender.get("login"), "url": sender.get("html_url")}

        # Collect all text sources for mention extraction
        mention_sources = []

        # Pull request event
        if "pull_request" in payload:
            pr = payload["pull_request"]
            pr_body = pr.get("body") or ""
            parsed["data"] = {
                "type": "pull_request",
                "number": pr.get("number"),
                "title": pr.get("title"),
                "body": pr_body,
                "state": pr.get("state"),
                "url": pr.get("html_url"),
                "head_branch": pr.get("head", {}).get("ref"),
                "base_branch": pr.get("base", {}).get("ref"),
                "commits_url": pr.get("commits_url"),
                "diff_url": pr.get("diff_url"),
                "patch_url": pr.get("patch_url"),
                "user": {"username": pr.get("user", {}).get("login"), "url": pr.get("user", {}).get("html_url")},
            }
            mention_sources.append(pr_body)

        # Issue event
        if "issue" in payload:
            issue = payload["issue"]
            issue_body = issue.get("body") or ""
            # Only set data if not already set by pull_request (issue_comment events have both)
            if parsed["data"].get("type") != "pull_request":
                parsed["data"] = {
                    "type": "issue",
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "body": issue_body,
                    "state": issue.get("state"),
                    "url": issue.get("html_url"),
                    "labels": [label.get("name") for label in issue.get("labels", [])],
                    "user": {
                        "username": issue.get("user", {}).get("login"),
                        "url": issue.get("user", {}).get("html_url"),
                    },
                }
            else:
                # Add issue reference for PR-related events
                parsed["data"]["issue"] = {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "url": issue.get("html_url"),
                }
            mention_sources.append(issue_body)

        # Comment event (issue_comment, pull_request_review_comment)
        if "comment" in payload:
            comment = payload["comment"]
            comment_body = comment.get("body") or ""
            parsed["data"]["comment"] = {
                "id": comment.get("id"),
                "body": comment_body,
                "user": comment.get("user", {}).get("login"),
                "user_url": comment.get("user", {}).get("html_url"),
                "html_url": comment.get("html_url"),
                "created_at": comment.get("created_at"),
                "updated_at": comment.get("updated_at"),
            }
            # Comment body is the primary source for mentions
            mention_sources.insert(0, comment_body)

        # Review event
        if "review" in payload:
            review = payload["review"]
            review_body = review.get("body") or ""
            parsed["data"]["review"] = {
                "id": review.get("id"),
                "body": review_body,
                "state": review.get("state"),
                "user": review.get("user", {}).get("login"),
                "html_url": review.get("html_url"),
                "submitted_at": review.get("submitted_at"),
            }
            mention_sources.append(review_body)

        # Push event
        if "commits" in payload and "pull_request" not in payload:
            parsed["data"] = {
                "type": "push",
                "ref": payload.get("ref"),
                "before": payload.get("before"),
                "after": payload.get("after"),
                "commits": [
                    {
                        "id": commit.get("id"),
                        "message": commit.get("message"),
                        "author": commit.get("author", {}).get("name"),
                        "url": commit.get("url"),
                    }
                    for commit in payload.get("commits", [])
                ],
            }
            # Extract mentions from commit messages
            for commit in payload.get("commits", []):
                mention_sources.append(commit.get("message") or "")

        # Extract mentions from all collected text sources
        all_mentions = []
        seen_mentions = set()
        for text in mention_sources:
            for mention in ProviderParser._extract_mentions(text):
                if mention.lower() not in seen_mentions:
                    seen_mentions.add(mention.lower())
                    all_mentions.append(mention)
        parsed["mentions"] = all_mentions

        return parsed

    @staticmethod
    def parse_clickup(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse ClickUp webhook payload.

        Supported events:
        - taskCreated
        - taskUpdated
        - taskDeleted
        - taskStatusUpdated
        - taskCommentPosted
        """
        event_type = payload.get("event", "unknown")

        parsed = {
            "provider": "clickup",
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "workspace_id": payload.get("webhook_id"),
            "data": {},
        }

        # Task data
        if "task_id" in payload:
            task = payload
            parsed["data"] = {
                "type": "task",
                "task_id": task.get("task_id"),
                "task_name": task.get("task_name"),
                "task_url": task.get("task_url"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "assignees": task.get("assignees", []),
                "tags": task.get("tags", []),
                "due_date": task.get("due_date"),
                "description": task.get("description"),
                "list_id": task.get("list_id"),
                "folder_id": task.get("folder_id"),
                "space_id": task.get("space_id"),
            }

        # History/changes data
        if "history_items" in payload:
            parsed["data"]["changes"] = payload.get("history_items", [])

        return parsed

    @staticmethod
    def parse_jira(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse Jira webhook payload.

        Supported events:
        - jira:issue_created
        - jira:issue_updated
        - jira:issue_deleted
        - comment_created
        - comment_updated
        """
        event_type = payload.get("webhookEvent", "unknown")

        parsed = {"provider": "jira", "event_type": event_type, "timestamp": datetime.now(UTC).isoformat(), "data": {}}

        # Issue data
        if "issue" in payload:
            issue = payload["issue"]
            fields = issue.get("fields", {})

            parsed["data"] = {
                "type": "issue",
                "issue_id": issue.get("id"),
                "issue_key": issue.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "url": issue.get("self"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
                "labels": fields.get("labels", []),
                "components": [c.get("name") for c in fields.get("components", [])],
                "created": fields.get("created"),
                "updated": fields.get("updated"),
            }

        # Comment data
        if "comment" in payload:
            comment = payload["comment"]
            parsed["data"]["comment"] = {
                "id": comment.get("id"),
                "body": comment.get("body"),
                "author": comment.get("author", {}).get("displayName"),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
            }

        # User who triggered the event
        if "user" in payload:
            user = payload["user"]
            parsed["user"] = {
                "username": user.get("name"),
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress"),
            }

        # Changelog for updates
        if "changelog" in payload:
            parsed["data"]["changelog"] = payload["changelog"]

        return parsed

    @staticmethod
    def parse_slack(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse Slack webhook payload.

        Supported events:
        - message
        - reaction_added
        - app_mention
        """
        event_type = payload.get("type", "unknown")

        parsed = {"provider": "slack", "event_type": event_type, "timestamp": datetime.now(UTC).isoformat(), "data": {}}

        # Handle event wrapper
        if "event" in payload:
            event = payload["event"]
            event_type = event.get("type", event_type)
            parsed["event_type"] = event_type

            parsed["data"] = {
                "type": event_type,
                "channel": event.get("channel"),
                "user": event.get("user"),
                "text": event.get("text"),
                "ts": event.get("ts"),
                "thread_ts": event.get("thread_ts"),
            }

            # Reaction event
            if event_type == "reaction_added":
                parsed["data"]["reaction"] = event.get("reaction")
                parsed["data"]["item"] = event.get("item")

        # Team info
        if "team_id" in payload:
            parsed["team_id"] = payload["team_id"]

        return parsed

    @staticmethod
    def parse_gitlab(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse GitLab webhook payload.

        Supported events:
        - merge_request (open, close, merge, update, reopen)
        - issue (open, close, reopen, update)
        - note (comment on MR, issue, commit, snippet)
        - push
        """
        object_kind = payload.get("object_kind", "unknown")
        object_attributes = payload.get("object_attributes", {})
        action = object_attributes.get("action") or object_attributes.get("state", "")

        # Build event type
        if action:
            event_type = f"{object_kind}.{action}"
        else:
            event_type = object_kind

        # Extract common fields
        parsed = {
            "provider": "gitlab",
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "project": None,
            "user": None,
            "data": {},
            "mentions": [],
        }

        # Collect text for mention extraction
        mention_sources = []

        # Project info
        if "project" in payload:
            project = payload["project"]
            parsed["project"] = {
                "id": project.get("id"),
                "name": project.get("name"),
                "path_with_namespace": project.get("path_with_namespace"),
                "web_url": project.get("web_url"),
                "default_branch": project.get("default_branch"),
            }

        # User info
        if "user" in payload:
            user = payload["user"]
            parsed["user"] = {
                "id": user.get("id"),
                "username": user.get("username"),
                "name": user.get("name"),
                "email": user.get("email"),
                "avatar_url": user.get("avatar_url"),
            }

        # Merge Request event
        if object_kind == "merge_request":
            mr = object_attributes
            mr_description = mr.get("description") or ""
            parsed["data"] = {
                "type": "merge_request",
                "iid": mr.get("iid"),
                "id": mr.get("id"),
                "title": mr.get("title"),
                "description": mr_description,
                "state": mr.get("state"),
                "url": mr.get("url"),
                "source_branch": mr.get("source_branch"),
                "target_branch": mr.get("target_branch"),
                "source_project_id": mr.get("source_project_id"),
                "target_project_id": mr.get("target_project_id"),
                "author_id": mr.get("author_id"),
                "assignee_id": mr.get("assignee_id"),
                "merge_status": mr.get("merge_status"),
                "work_in_progress": mr.get("work_in_progress"),
            }
            mention_sources.append(mr_description)

        # Issue event
        elif object_kind == "issue":
            issue = object_attributes
            issue_description = issue.get("description") or ""
            parsed["data"] = {
                "type": "issue",
                "iid": issue.get("iid"),
                "id": issue.get("id"),
                "title": issue.get("title"),
                "description": issue_description,
                "state": issue.get("state"),
                "url": issue.get("url"),
                "labels": [label.get("title") for label in payload.get("labels", [])],
                "author_id": issue.get("author_id"),
                "assignee_ids": issue.get("assignee_ids", []),
            }
            mention_sources.append(issue_description)

        # Note (comment) event
        elif object_kind == "note":
            note = object_attributes
            note_body = note.get("note") or ""
            noteable_type = note.get("noteable_type", "").lower()

            parsed["data"] = {
                "type": "note",
                "noteable_type": noteable_type,
                "comment": {
                    "id": note.get("id"),
                    "body": note_body,
                    "url": note.get("url"),
                    "author_id": note.get("author_id"),
                    "created_at": note.get("created_at"),
                    "updated_at": note.get("updated_at"),
                },
            }

            # Add MR/issue context if present
            if "merge_request" in payload:
                mr = payload["merge_request"]
                parsed["data"]["merge_request"] = {
                    "iid": mr.get("iid"),
                    "id": mr.get("id"),
                    "title": mr.get("title"),
                    "state": mr.get("state"),
                    "url": mr.get("url"),
                    "source_branch": mr.get("source_branch"),
                    "target_branch": mr.get("target_branch"),
                }
            elif "issue" in payload:
                issue = payload["issue"]
                parsed["data"]["issue"] = {
                    "iid": issue.get("iid"),
                    "id": issue.get("id"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "url": issue.get("url"),
                }
            elif "commit" in payload:
                commit = payload["commit"]
                parsed["data"]["commit"] = {
                    "id": commit.get("id"),
                    "message": commit.get("message"),
                    "url": commit.get("url"),
                }

            # Note body is primary mention source
            mention_sources.insert(0, note_body)

        # Push event
        elif object_kind == "push" or "commits" in payload:
            parsed["data"] = {
                "type": "push",
                "ref": payload.get("ref"),
                "before": payload.get("before"),
                "after": payload.get("after"),
                "checkout_sha": payload.get("checkout_sha"),
                "total_commits_count": payload.get("total_commits_count"),
                "commits": [
                    {
                        "id": commit.get("id"),
                        "message": commit.get("message"),
                        "author": commit.get("author", {}).get("name"),
                        "url": commit.get("url"),
                        "added": commit.get("added", []),
                        "modified": commit.get("modified", []),
                        "removed": commit.get("removed", []),
                    }
                    for commit in payload.get("commits", [])
                ],
            }
            # Extract mentions from commit messages
            for commit in payload.get("commits", []):
                mention_sources.append(commit.get("message") or "")

        # Extract mentions
        all_mentions = []
        seen_mentions = set()
        for text in mention_sources:
            for mention in ProviderParser._extract_mentions(text):
                if mention.lower() not in seen_mentions:
                    seen_mentions.add(mention.lower())
                    all_mentions.append(mention)
        parsed["mentions"] = all_mentions

        return parsed

    @staticmethod
    def parse_sentry(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse Sentry webhook payload.

        Handles two formats:
        - Legacy Webhooks plugin (Settings → Integrations → Webhooks):
          Top-level fields: project, level, culprit, message, url, event{}
        - New Alerts API (Alerts → Alert Rules → Webhook action):
          Top-level fields: action, resource, data{issue{}, event{}}
        """
        # Detect format: legacy has top-level "event" but no "action"/"resource"
        is_legacy = "action" not in payload and "event" in payload

        if is_legacy:
            # Legacy Webhooks plugin format
            inner_event = payload.get("event", {})
            event_type = "error"
            return {
                "provider": "sentry",
                "event_type": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "action": "triggered",
                    "issue_id": inner_event.get("event_id") or inner_event.get("id"),
                    "issue_title": inner_event.get("title") or payload.get("message", ""),
                    "issue_url": payload.get("url", ""),
                    "level": payload.get("level") or inner_event.get("level", ""),
                    "culprit": payload.get("culprit") or inner_event.get("culprit", ""),
                    "project": payload.get("project_slug") or payload.get("project", ""),
                    "status": "",
                    "times_seen": 0,
                    "first_seen": "",
                    "last_seen": "",
                    "stack_trace": inner_event.get("sentry.interfaces.Stacktrace", {})
                    or inner_event.get("stacktrace", {}),
                    "tags": inner_event.get("tags", []),
                    "raw": payload,
                },
            }

        # New Alerts API format
        action = payload.get("action", "")
        data = payload.get("data", {})
        issue = data.get("issue", {})
        event = data.get("event", {})
        resource = payload.get("resource", "")

        if resource == "event_alert":
            event_type = "event_alert"
        elif resource == "metric_alert":
            event_type = "metric_alert"
        elif action == "created":
            event_type = "issue"
        elif action == "triggered":
            event_type = "issue_alert"
        else:
            event_type = action or "error"

        return {
            "provider": "sentry",
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "action": action,
                "issue_id": issue.get("id"),
                "issue_title": issue.get("title") or event.get("title", ""),
                "issue_url": issue.get("web_url") or issue.get("permalink", ""),
                "level": issue.get("level") or event.get("level", ""),
                "culprit": issue.get("culprit") or event.get("culprit", ""),
                "project": issue.get("project", {}).get("slug") if isinstance(issue.get("project"), dict) else "",
                "status": issue.get("status", ""),
                "times_seen": issue.get("times_seen", 0),
                "first_seen": issue.get("firstSeen", ""),
                "last_seen": issue.get("lastSeen", ""),
                "stack_trace": event.get("sentry.interfaces.Stacktrace", {}) or event.get("stacktrace", {}),
                "tags": event.get("tags", []),
                "raw": payload,
            },
        }

    @staticmethod
    def parse_custom(payload: dict[str, Any], config: dict | None = None) -> dict[str, Any]:
        """
        Parse custom webhook payload.

        Uses configuration to extract specific fields.
        """
        config = config or {}

        # Default to "webhook" so it matches the standard custom event_type selection
        event_type = "webhook"

        # Extract event type from payload if configured
        if "event_type_field" in config:
            event_type_path = config["event_type_field"].split(".")
            value = payload
            for key in event_type_path:
                value = value.get(key, "webhook")
                if not isinstance(value, dict):
                    break
            event_type = value

        parsed = {
            "provider": "custom",
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": payload,
        }

        return parsed

    @classmethod
    def parse(cls, provider: str, payload: dict[str, Any], config: dict | None = None) -> dict[str, Any]:
        """
        Parse webhook payload based on provider.

        Args:
            provider: Provider name
            payload: Raw webhook payload
            config: Additional configuration

        Returns:
            Parsed data in standardized format
        """
        if provider == "github":
            return cls.parse_github(payload)
        elif provider == "gitlab":
            return cls.parse_gitlab(payload)
        elif provider == "clickup":
            return cls.parse_clickup(payload)
        elif provider == "jira":
            return cls.parse_jira(payload)
        elif provider == "slack":
            return cls.parse_slack(payload)
        elif provider == "sentry":
            return cls.parse_sentry(payload)
        elif provider == "custom":
            return cls.parse_custom(payload, config)
        else:
            # Unknown provider - return raw payload
            return {
                "provider": provider,
                "event_type": "unknown",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": payload,
            }
