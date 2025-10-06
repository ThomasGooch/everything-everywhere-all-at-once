# AI Development Automation System

A complete end-to-end automation system that integrates Jira task management, Claude CLI development sessions, and GitHub workflow automation.

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** with Poetry installed
2. **Claude CLI** installed and configured
3. **Git** configured with SSH access to your repositories
4. **Environment Variables** configured for Jira integration

### Environment Setup

Create a `.env` file with your Jira credentials:

```bash
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_API_KEY=your_api_key
JIRA_USERNAME=your_email@domain.com
JIRA_PROJECT_KEY=YOUR_PROJECT_KEY
```

### Installation

```bash
# Install dependencies
poetry install

# Verify Claude CLI is available
claude --version
```

## 🎯 Main Workflow

### Usage

Run the complete automated development workflow:

```bash
poetry run python real_development_workflow_by_id.py TASK-123
```

Replace `TASK-123` with your actual Jira task ID.

### What Happens

1. **📋 Fetches task from Jira** - Gets task details and validates access
2. **🔄 Moves task to In Progress** - Updates Jira status automatically  
3. **💬 Adds automation comment** - Documents workflow start in Jira
4. **📁 Clones repository** - Downloads repo to `./temp` directory
5. **🌿 Creates feature branch** - Names it `TASK-ID_summary_timestamp`
6. **🚀 Launches Claude CLI** - Opens Terminal session in repo directory
7. **⏳ Waits for completion** - Monitors until you exit Claude CLI
8. **🔧 Auto-completion** - When you exit Claude CLI:
   - ✅ Commits and pushes your changes
   - ✅ Creates GitHub pull request
   - ✅ Updates Jira task to Done
   - ✅ Adds completion comment with PR link
   - ✅ Cleans up `./temp` directory completely

### Your Experience

1. **Run the command** - The workflow launches
2. **Terminal opens** - Claude CLI starts in the repository directory
3. **Work with Claude** - Implement features, create files, make changes
4. **Exit Claude CLI** - Press Ctrl+C or type `exit`
5. **Everything else is automatic** - PR created, Jira updated, cleanup done

## 🔧 Manual Completion (If Needed)

If the workflow gets interrupted, you can manually complete it:

```bash
poetry run python complete_workflow.py TASK-123 branch-name
```

This will finish the remaining steps: commit, push, PR creation, Jira updates, and cleanup.

## 📁 Project Structure

```
├── real_development_workflow_by_id.py  # Main workflow script
├── complete_workflow.py               # Manual completion utility  
├── core/                              # Core system components
│   ├── plugin_interface.py           # Base plugin interfaces
│   ├── plugin_registry.py            # Plugin management
│   └── exceptions.py                  # Custom exceptions
├── plugins/                           # Plugin implementations
│   └── jira/                         # Jira integration
│       ├── api.py                    # Jira API wrapper
│       ├── config.py                 # Configuration management
│       └── tools.py                  # Jira utilities
└── docs/                             # Documentation
    └── getting_started.md           # Detailed setup guide
```

## 🎯 Key Features

### ✅ Complete Automation
- **End-to-end workflow** from Jira task to merged PR
- **No manual steps** after launching Claude CLI
- **Automatic cleanup** - temp directory is always empty after completion

### ✅ Robust Integration  
- **Real Jira API calls** - Updates actual task status and comments
- **GitHub integration** - Creates proper pull requests with detailed descriptions
- **Claude CLI integration** - Full development environment with all tools available

### ✅ Development-Friendly
- **All dev tools available** - dotnet, python3, node, git work in Claude CLI session
- **Proper git workflow** - Feature branches, meaningful commit messages
- **Error handling** - Graceful recovery from interruptions

### ✅ Smart Monitoring
- **Process detection** - Automatically detects when Claude CLI session ends
- **File-based markers** - Reliable completion detection mechanism  
- **Timeout protection** - Won't hang indefinitely

## 🛠️ Advanced Configuration

### Repository Configuration

Edit the repository URL in `real_development_workflow_by_id.py`:

```python
self.repo_url = "git@github.com:YourUsername/YourRepo.git"
```

### Timeout Settings

The workflow waits up to 1 hour for Claude CLI sessions. Modify in the code:

```python
max_wait_time = 3600  # seconds
```

### Branch Naming

Branch names follow the pattern: `TASK-ID_summary_timestamp`

Example: `JIRA-123_implement_user_auth_152830`

## 🎉 Success Indicators

When the workflow completes successfully, you'll see:

- ✅ **GitHub PR created** with your changes
- ✅ **Jira task moved to Done** with completion comment
- ✅ **Temp directory empty** - no leftover files
- ✅ **All changes committed** and pushed to remote branch

## 📞 Support

### Common Issues

1. **"Jira API not available"** - Check your `.env` file and credentials
2. **"Claude CLI not found"** - Ensure Claude CLI is installed and in PATH
3. **"Repository clone failed"** - Verify SSH key setup for GitHub
4. **"No changes detected"** - Make sure files are saved in the temp directory

### Getting Help

1. Check the detailed setup guide: `docs/getting_started.md`
2. Verify your environment variables are configured
3. Test Claude CLI works independently: `claude --version`
4. Ensure your Jira API key has proper permissions

## 🚀 What Makes This Special

This system provides a **complete development automation experience**:

- **Start with a Jira task** - Just provide the task ID
- **Work naturally with Claude CLI** - Full development environment
- **End with a ready PR** - Everything documented and organized
- **Zero cleanup needed** - System manages all temporary files

Perfect for rapid development cycles, feature implementation, and maintaining clean git history while leveraging AI-powered development assistance.