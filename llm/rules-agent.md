These rules define how to write, structure, and manage code in this project.  
Keep everything simple, consistent, and easy to maintain.

## Internal Files
- llm/state-project.md: project status, update gradually
- llm/state-frontend.md: frontend architecture,update gradually
- llm/state-backend.md: backend architecture, update gradually
- llm/rules-backend.md: backend coding standards (follow for backend tasks)
- llm/rules-frontend.md: frontend coding standards (follow for frontend tasks)
- llm/rules-agent.md: agent behavior guidelines

---

## Code Style
- comments start in lowercase and explain why, not what. The code should already explain what it does.  
- write the minimal number of functions and comments needed.  
- avoid unnecessary `else` blocks; return early when possible.  
- keep names clear, functions small, and logic simple.  
- make the code slightly better than you found it, but don’t rebuild.

---

## Commit Rules
- never commit or push unless explicitly asked to.  
- commit message format:
```
[fix|edit|...]: short description (max 50 chars)
```
examples:  
- `fix: prevent double API call`  
- `feat: add user search`  
- `clean: remove unused import`  
- always ask for confirmation before committing.  

---

## Key Principles
1. simplicity over cleverness.  
2. clarity over abstraction.  
3. explain intent, not mechanics.  
4. one step better, not a full rewrite.  