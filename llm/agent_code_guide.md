These rules define how to write, structure, and manage code in this project.  
Keep everything simple, consistent, and easy to maintain.


## Internal Files
- llm/project_technical_guide.md: used only to track current project status across multiple sessions to avoid re-exploration. Never commit it. You have to update gradually.
- llm/frontend_technical_guide.md: describes UI design and layout decisions. Never commit it. You have to update gradually.
- llm/backend_technical_guide.md: describes backend logic and architecture. Never commit it. You have to update gradually.
- for tasks related to backend ensure to follow the backend_code_guide.md
- for tasks related to frontend ensure to follow the frontend_code_guide.md

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