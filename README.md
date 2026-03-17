# Decision OS

Decision OS is a Notion-powered workflow tool that turns messy team notes into structured decisions, follow-up tasks, and a clean operational record.

## The Problem

Teams often capture discussions in messy notes, but the final decision, rationale, owner, and next steps get lost. As a result, work becomes scattered and it becomes hard to understand what was decided, why it was decided, and what needs to happen next.

## The Solution

Decision OS uses Notion as the central workspace for decision tracking.

A user adds raw notes into a **Notes Inbox** in Notion. The app reads those notes, extracts structured decision information, creates a decision entry in a **Decisions** database, creates a follow-up task in a **Tasks** database, and marks the original note as processed.

This creates a lightweight decision memory system for teams.

## Features

- Reads raw notes from a Notion **Notes Inbox**
- Extracts a structured decision from unstructured text
- Generates a short summary and rationale
- Identifies likely owner and follow-up task
- Creates a new entry in the **Decisions** database
- Creates a new entry in the **Tasks** database
- Marks processed notes automatically
- Displays recent decisions and open tasks in a clean dashboard

## How It Works

1. A user adds messy meeting or discussion notes into the **Notes Inbox** database in Notion.
2. Decision OS reads all notes from the inbox.
3. The app extracts:
   - decision title
   - summary
   - rationale
   - owner
   - project
   - follow-up task
   - due date / revisit date when available
4. The app writes the extracted information into the **Decisions** database.
5. It creates a related follow-up task in the **Tasks** database.
6. It marks the original note as processed.


## Notion Workspace Structure

The system uses three Notion databases:

### 1. Notes Inbox
Stores raw notes that have not yet been processed.

### 2. Decisions
Stores structured decisions, summaries, rationale, status, project, owner, and dates.

### 3. Tasks
Stores follow-up actions linked to decisions.

