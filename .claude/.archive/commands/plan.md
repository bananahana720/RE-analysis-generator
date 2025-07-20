# AI-Led Strategic Grooming Command

**Lead Agent Directive:**

You are to initiate the **Strategic Grooming Process** for the upcoming sprint. Your role is not to ask me questions immediately, but to first perform a comprehensive, autonomous analysis and come to me with a proposed plan and identified risks.

**CRITICAL**: You are expected to operate with a high degree of autonomy. Use the `ultrathink` directive when making decisions about spawning sub-agents or handling errors.

**MUST** REFRESH MEMORY OF project ruleset in root project directory [CLAUDE.md MUST REFERENCE](CLAUDE.md)
- You **must** maintain consistent, structured memory across conversations, enabling richer and more dynamic interactions.
Refer to [Memory Bank](/memory_bank/)
- [memory_bank template](/memory_bank/MEMORY-SYSTEM.md)

**Execution Flow:**

1.  **Phase 1: Autonomous Analysis (The Deep Dive)**
    * **Objective**: To fully understand the upcoming sprint's epics and their implications *without user input*.
    * **Action**:
        1.  Identify the epics for the current sprint from `/memory_bank/sprints/current/` (if does not exist stale or , create folder or move sprint .md files to separate numbered sprint folder for archival).
        2.  For each epic, **generate a dynamic analysis strategy**. This strategy should involve spawning multiple, parallel sub-agents.
        3.  **Spawn Sub-Agents**:
            * `Dependency-Agent`: Scours the codebase and memory to identify all potential upstream and downstream dependencies. use `zen-mcp` mcp tools for outside perspective and help!
            * `Risk-Agent`: Analyzes the epic for potential risks (e.g., architectural conflicts, missing data, complex UI). It should use `ultrathink` to brainstorm "what could go wrong?". use `zen-mcp` mcp tools for outside perspective and help!
            * `Research-Agent`: Search your memory for relevant and precise information. If the epic involves new technologies or libraries, this agent performs web searches for best practices and documentation using `fetch` and `Context7` MCP tools.
            * `Test-Strategy-Agent`: Proposes a high-level testing strategy for the epic, referencing `CLAUDE.md`. use `zen-mcp` mcp tools for outside perspective and help!

2.  **Phase 2: Synthesis & Proposal**
    * **Objective**: To consolidate the findings from all sub-agents into a single, actionable "Grooming Dossier" for each epic.
    * **Action**:
        1.  Collect the reports from all sub-agents.
        2.  Synthesize their findings into a dossier that includes:
            -   A summary of the epic's goal.
            -   A list of identified dependencies and risks.
            -   A proposed technical approach and testing strategy.
            -   A list of "Decision Points"—critical questions that require human input.
        3.  Store this dossier in memory.

3.  **Phase 3: Interactive Review (Engage the User)**
    * **Objective**: To present your findings to the Product Owner for final decisions.
    * **Action**:
        1.  "I have completed my autonomous analysis of the upcoming sprint. Here is the Grooming Dossier for the first epic. Let's review the 'Decision Points' I've identified."
        2.  Facilitate the discussion based on your prepared analysis.

**CRITICAL**: Use memory_bank/ throughout this process to:
- Load previous sprint context
- Store grooming decisions
- Track action items
- Maintain persistent understanding of project state
[Memory Template](/memory_bank/MEMORY-SYSTEM.md)

**Follow these steps:**

1.  **Sprint Initialization**:
    * Load all necessary context from `memory_bank/`, including `sprints/current`, relevant ADRs, and `development/blockers/`.
    * Identify the current sprint from `memory_bank/sprints/current/`.

2.  **Automated Epic Analysis (Sub-Agent Dispatch)**:
    * For each epic in the current sprint that needs grooming, you MUST follow the **"Epic Grooming & Analysis"** orchestration pattern defined in `/CLAUDE.md`.
    * Spawn a `Research-Agent` and a `Technical-Analyst-Agent` in parallel.
    * **Your Task**: Synthesize the reports from these agents into a "Grooming Brief" for each epic. This brief should include a summary of findings, a list of potential challenges, and a set of proposed clarifying questions.

3. **Review Process**: Refer to `docs/planning/sprint-grooming-process.md` for the detailed steps of "Epic Grooming (Iterative Discussion)".

4. **Determine Grooming Needs**:
   - List all epic markdown files within the `memory_bank/sprints/current/` directory.
   - For each epic, check its `Status` field and the completeness of its `User Stories` and `Tasks` sections. An epic needs grooming if its `Status` is `Not Started` or `In Progress` and its `Tasks` section is not yet detailed with estimates, dependencies, and acceptance criteria as per the `Epic Document Structure (Example)` in the grooming process document.

5. **Initiate Grooming**:
   - If there are epics identified in Step 4 that require grooming, select the next one.
   - Begin an interactive grooming session with the Product Owner. Your primary role is to ask clarifying questions (as exemplified in Section 2 of the grooming process document) to:

     **Relevance/Value**:
     - "How does this epic directly contribute to our current MVP success metrics?"
     - "What specific user pain does it alleviate?"

     **User Stories**:
     - "Are these user stories truly from the user's perspective?"
     - "Do they capture the 'why' behind the 'what'?"
     - "Can we add acceptance criteria to each story?"

     **Technical Deep Dive**:
     - "What are the primary technical challenges you foresee in implementing this?"
     - "Are there any external services or APIs we'll need to integrate with?"
     - "What are the potential performance implications?"

     **Dependencies**:
     - "Does this epic depend on any other epics in this sprint or future sprints?"
     - "Are there any external teams or resources we'll need?"

     **Edge Cases/Error Handling**:
     - "What happens if [X unexpected scenario] occurs?"
     - "How should the system behave?"
     - "What kind of error messages should the user see?"

     **Data Model Impact**:
     - "How will this epic impact our BigQuery schema analysis models?"
     - "Are there new data structures or relationships required?"

     **Testing Strategy**:
     - "What specific types of tests (unit, integration, end-to-end) will be critical for this epic?"
     - "Are there any complex scenarios that will be difficult to test?"

   - **Propose direct updates to the epic's markdown file** (`memory_bank/sprints/current/<epic_name>.md`) to capture all discussed details.
   - Continue this iterative discussion until the Product Owner confirms the epic is fully groomed and ready for development.
   - Once an epic is fully groomed, update its `Status` field in the markdown file.

6. **Store Grooming Decisions**:
   - Save all decisions to memory_bank under `memory_bank/sprints/current/grooming-decisions/<epic-name>`
   - Update memory with any new technical insights discovered under `memory_bank/patterns/`
   - Record any architectural implications for future ADRs under `memory_bank/architecture/decisions/`

7. **Sprint Completion Check**:
   - If all epics in the current sprint directory (`memory_bank/sprints/current/`) have been fully groomed (i.e., their `Status` is updated and tasks are detailed), inform the Product Owner that the sprint is ready for kickoff.
   - Store sprint summary in memory_bank at `memory_bank/sprints/current/ready-for-development`
   - Ask the Product Owner if they would like to proceed with setting up the development environment (referencing Sprint 1 tasks) or move to planning the next sprint.

8.  **Error Handling Protocol**:
    * If you encounter a malformed epic file or fail to load context from memory, **do not halt**.
    * Engage `ultrathink` mode to analyze the error.
    * **Attempt a fix**: If the error is simple (e.g., a missing field), you may propose a fix to the file.
    * **Request Help**: If the error is complex or ambiguous, clearly articulate the problem and the attempted solutions to the Product Owner and ask for guidance.


**Benefits of This Process:**
- Avoids context problems with high-complexity projects because all relevant information is captured in sprint planning docs
- Encourages Claude to dive MUCH deeper into problem solving without extensive high-level brainstorming
- Prevents large sweeping decisions without consultation - grooming discovers key decisions BEFORE coding begins
- A completely clean context window can quickly understand where we are and resume right where we left off

**Important Notes:**
- Always reference the current sprint goals from CLAUDE.md
- Use sequential thinking for complex architectural discussions
- Store all significant decisions in memory_bank
- Create ADRs for major architectural choices
