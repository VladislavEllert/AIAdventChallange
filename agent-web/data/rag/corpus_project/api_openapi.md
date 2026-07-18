<!-- source: agent-web/agent_web/app.py | title: API openapi schema -->

# API — Agent Web 0.1.0

## Paths

### POST /api/chat/stream
Chat Stream
- has request body (see Schemas below)

### GET /api/sessions
List Sessions
- param `agent_id` (query) required=False
- param `owner` (query) required=False

### POST /api/sessions
Create Session
- has request body (see Schemas below)

### GET /api/sessions/{session_id}
Get Session
- param `session_id` (path) required=True

### PUT /api/sessions/{session_id}
Rename Session
- param `session_id` (path) required=True
- has request body (see Schemas below)

### DELETE /api/sessions/{session_id}
Delete Session
- param `session_id` (path) required=True

### GET /api/models
List Models

### GET /api/models/default
Default Model

### GET /api/agents
List Agents

### POST /api/agents
Create Agent
- has request body (see Schemas below)

### PUT /api/agents/{agent_id}
Update Agent
- param `agent_id` (path) required=True
- has request body (see Schemas below)

### DELETE /api/agents/{agent_id}
Delete Agent
- param `agent_id` (path) required=True

### GET /api/memory/{session_id}
Get Memory
- param `session_id` (path) required=True

### POST /api/memory/{session_id}/extract-profile
Extract Profile Facts
- param `session_id` (path) required=True
- param `profile_name` (query) required=True

### GET /api/invariants
List Invariants

### POST /api/invariants
Create Invariant
- has request body (see Schemas below)

### DELETE /api/invariants/{index}
Remove Invariant
- param `index` (path) required=True

### GET /api/profiles
List Profiles

### GET /api/profiles/{name}
Get Profile
- param `name` (path) required=True

### PUT /api/profiles/{name}
Update Profile
- param `name` (path) required=True
- has request body (see Schemas below)

### GET /api/tasks
List Tasks

### POST /api/tasks
Create Task
- has request body (see Schemas below)

### GET /api/tasks/{task_id}
Get Task
- param `task_id` (path) required=True

### GET /api/tasks/{task_id}/stream
Stream Task
- param `task_id` (path) required=True

### POST /api/tasks/{task_id}/feedback
Task Feedback
- param `task_id` (path) required=True
- has request body (see Schemas below)

### GET /api/settings
Get Settings

### PUT /api/settings
Update Settings
- has request body (see Schemas below)

### GET /api/metrics
Get Metrics

### GET /api/health
Health

## Schemas

### AgentCreate
- `name`: string
- `emoji`: string
- `system_prompt`: string

### AgentOut
- `id`: string
- `name`: string
- `emoji`: string
- `system_prompt`: string
- `created_at`: number

### AgentUpdate
- `name`: any
- `emoji`: any
- `system_prompt`: any

### ChatRequest
- `session_id`: string
- `message`: string
- `image_b64`: any
- `persona`: any
- `model`: any
- `profile_name`: any
- `use_rag`: boolean
- `use_mcp`: boolean

### FeedbackBody
- `action`: string
- `text`: string

### HTTPValidationError
- `detail`: array

### InvariantCreate
- `text`: string

### MessageOut
- `role`: string
- `content`: string

### ModelInfo
- `model_id`: string
- `input_price`: number
- `output_price`: number
- `type`: string

### ProfileUpdate
- `content`: string

### SessionCreate
- `name`: string
- `agent_id`: any
- `owner`: string

### SessionDetail
- `session_id`: string
- `name`: string
- `display_name`: string
- `model`: string
- `profile_name`: string
- `summary`: string
- `messages`: array
- `cost_rub`: number

### SessionOut
- `session_id`: string
- `name`: string
- `display_name`: string
- `created_at`: number
- `updated_at`: number
- `profile_name`: string
- `model`: string
- `msg_count`: integer
- `cost_rub`: number
- `owner`: string

### SessionRename
- `name`: string

### SettingsPatch
- `short_term_limit`: any
- `keep_recent`: any
- `default_model`: any
- `auto_profile_update`: any
- `theme`: any
- `temperature`: any
- `max_tokens`: any
- `top_p`: any
- `num_ctx`: any
- `image_steps`: any
- `image_cfg`: any
- `image_seed`: any
- `image_width`: any
- `image_height`: any
- `image_seed_random`: any

### TaskCreate
- `request`: string
- `model`: string
- `profile_content`: string

### ValidationError
- `loc`: array
- `msg`: string
- `type`: string
- `input`: any
- `ctx`: object
