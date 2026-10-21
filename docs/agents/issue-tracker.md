# Issue tracker: GitHub (via MCP)

Issues and specs for this repo live as GitHub issues on `the-dr-lazy/delmir`. Use the **GitHub MCP server** tools for all operations. Fall back to the `gh` CLI only for operations the MCP server doesn't provide (listed under **`gh` fallbacks** below).

Every call takes `owner: "the-dr-lazy"` and `repo: "delmir"`.

## Conventions

- **Create an issue**: `issue_write` with `method: "create"`, `title`, `body`, and optionally `labels`.
- **Read an issue**: `issue_read` with `method: "get"` and `issue_number`; use `method: "get_comments"` for its comments and `method: "get_labels"` for its labels.
- **List issues**: `list_issues` with `state` (`OPEN` / `CLOSED`) and `labels` filters. Pass `fields` to trim the payload.
- **Search issues**: `search_issues` with a natural-language `query`, scoped with `owner` and `repo`. Search before creating, to avoid duplicates.
- **Hierarchy**: model every parent/child relationship (spec → tickets, epic → tasks, map → children) as GitHub **sub-issues**. Don't use task lists or `Part of #<n>` lines in the body.
  - **Create a child**: `issue_write` with `method: "create"` and `parent_issue_number`.
  - **Attach an existing issue**: `sub_issue_write` with `method: "add"`, the parent's `issue_number`, and the child's `sub_issue_id` (the issue's numeric **id**, not its `#number`; read it from `issue_read` `get`). Add `replace_parent: true` to move it from another parent.
  - **Detach / reorder**: `sub_issue_write` with `method: "remove"` or `"reprioritize"` (`after_id` / `before_id`).
  - **Walk the tree**: `issue_read` with `method: "get_sub_issues"` for children, `method: "get_parent"` for the parent.
- **Comment on an issue**: `add_issue_comment` with `issue_number` and `body`.
- **Apply / remove labels**: `issue_write` with `method: "update"` and the issue's full desired `labels` list (it replaces the set, so read the current labels first and add or drop from that list).
- **Close**: `add_issue_comment` with the reason, then `issue_write` with `method: "update"`, `state: "closed"`, and `state_reason` (`completed`, `not_planned`, or `duplicate` with `duplicate_of`).

## `gh` fallbacks

For gaps in the MCP server only. Run inside the clone so `gh` infers the repo.

- **Create a label**: `gh label create "<name>" --description "..." --color <hex>`. (Applying a missing label with `issue_write` also creates it, with a default colour.)
- **Add a blocking edge**: `gh api --method POST repos/the-dr-lazy/delmir/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **id** from `issue_read` `get` (not its `#number`).
- **Read blockers**: `gh api repos/the-dr-lazy/delmir/issues/<n> --jq .issue_dependencies_summary.blocked_by` (open blockers only).

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues:

- **Read a PR**: `pull_request_read` with `method: "get"`, `"get_comments"`, or `"get_diff"`.
- **List external PRs for triage**: `list_pull_requests` with `state: "open"`, then drop those whose author is the owner or a collaborator.
- **Comment / label / close**: `add_issue_comment` and `issue_write` with the PR number as `issue_number` (GitHub treats PRs as issues for these).

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: try `pull_request_read` first and fall back to `issue_read`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue with `issue_write`.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue** above.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `issue_write` `create` with `labels: ["wayfinder:map"]`.
- **Child ticket**: a sub-issue of the map (see **Hierarchy**). Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies**, added and read via the `gh` fallbacks above (the MCP server has no tool for them). If that fails, record blockers as a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: `issue_read` `get_sub_issues` on the map, keep the open ones, drop any with an open blocker (`blocked_by > 0`, or an open issue in its `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `get_me` for the current login, then `issue_write` `update` with `assignees: [<login>]`, the session's first write.
- **Resolve**: `add_issue_comment` with the answer, then `issue_write` `update` with `state: "closed"`, then append a context pointer (gist + link) to the map's Decisions-so-far.
