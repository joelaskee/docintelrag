# Chat Persistence & Memory Plan

## 1. Problem Analysis
Currently, the chat is **stateless**:
1.  **No Storage**: Chat history is not saved in the database. When you refresh the page, messages disappear.
2.  **No Context Awareness**: Even if the frontend sends `history` in the API request, the backend **ignores it** when constructing the LLM prompt. The bot doesn't know what was said 2 seconds ago.

## 2. Proposed Solution
We will implement persistent chat history and inject previous context into the LLM prompt.

### 2.1 Database Schema
We need two new tables to store conversations.

**Table: `chat_sessions`**
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users)
- `title` (String) - generated from first message
- `created_at` (Timestamp)
- `updated_at` (Timestamp)

**Table: `chat_messages`**
- `id` (UUID)
- `session_id` (UUID, FK -> chat_sessions)
- `role` (Enum: 'user', 'assistant')
- `content` (Text)
- `created_at` (Timestamp)
- `tokens_used` (Integer, optional)

### 2.2 Backend Implementation

#### A. Database Models & Migration
- Define SQLAlchemy models for `ChatSession` and `ChatMessage`.
- Create Alembic migration.

#### B. API Updates (`/chat`)
- **GET /chat/sessions**: List user's past conversations.
- **GET /chat/sessions/{id}**: Get messages for a specific session.
- **POST /chat**:
    - Accept `session_id` (optional). If missing, create new session.
    - Save User Message to DB.
    - **Inject History**: Retrieve last N messages (e.g., 5) from DB.
    - Pass history to `RAGService` / `VLMService`.
    - Save Assistant Response to DB.
    - Return `session_id` and complete response.

#### C. Context Injection (The "Memory")
Modify `rag.py` (and `bi.py`) prompt construction:

```python
prompt = f"""...
CRONOLOGIA CHAT RECENTE:
User: Ciao
Assistant: Ciao! Come posso aiutarti?
User: Parlami della fattura 123
Assistant: La fattura 123 è di 500 euro.

DOMANDA CORRENTE: A chi è intestata?
..."""
```
*Note: "A chi è intestata?" now makes sense because the context "fattura 123" is present.*

### 2.3 Frontend Implementation
- **Sidebar History**: Add a sidebar/list to show past chats.
- **Session Management**:
    - When opening chat, load previous sessions.
    - When sending first message, set the new `session_id` returned by backend.
    - "New Chat" button to clear `session_id` and start fresh.

## 3. Task Breakdown

### Phase 1: Persistence (Backend)
- [ ] Create DB Models & Migration (`chat_sessions`, `chat_messages`)
- [ ] Implement `ChatService` to handle saving/loading.
- [ ] Update `POST /chat` to save messages.
- [ ] Implement `GET /chat/history` (or sessions).

### Phase 2: Context Awareness (Logic)
- [ ] Update `RAGService` prompt to include chat history.
- [ ] Update `BIService` to handle "follow-up" questions (e.g., "And the average?").

### Phase 3: UI (Frontend)
- [ ] Add "New Chat" button.
- [ ] (Optional MVP) Load history on refresh (restore state).

## 4. Testing Criteria
- **Persistence**: Refresh page -> Messages reappear.
- **Context**:
    1. User: "Cerca la fattura 10."
    2. Bot: "Ecco la fattura 10..."
    3. User: "Chi è il fornitore?" (Implicit subject)
    4. Bot: "Il fornitore è [Nome Correcto]" (instead of "Di quale documento parli?").
