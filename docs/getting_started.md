# Getting Started - AI Development Automation System

This guide will walk you through setting up and using the AI Development Automation System for the first time.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Python 3.11 or higher** installed
- [ ] **Poetry** package manager installed  
- [ ] **Claude CLI** installed and configured
- [ ] **Git** configured with SSH keys for GitHub
- [ ] **Jira API access** with an API key
- [ ] **Terminal/Command line** access

## 🔧 Step-by-Step Setup

### 1. Install Python Dependencies

```bash
# Navigate to the project directory
cd /path/to/ai-development-automation

# Install dependencies with Poetry
poetry install

# Verify installation
poetry run python --version
```

### 2. Configure Claude CLI

Ensure Claude CLI is installed and working:

```bash
# Check Claude CLI is available
claude --version

# Test Claude CLI (should open interactive session)
claude --print "Hello, Claude!"
```

If Claude CLI isn't installed, visit the [Claude CLI documentation](https://docs.anthropic.com/en/docs/claude-code) for installation instructions.

### 3. Set Up Jira Integration

#### Get Your Jira API Key

1. **Log in to Jira** in your web browser
2. **Go to Account Settings** (click your profile picture → Account settings)
3. **Navigate to Security** tab
4. **Create API token** - Click "Create API token"
5. **Copy the token** - Save it securely (you won't see it again)

#### Create Environment File

Create a `.env` file in the project root:

```bash
# Create the .env file
touch .env

# Add your Jira configuration
cat > .env << EOF
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_API_KEY=your_api_key_here
JIRA_USERNAME=your-email@company.com
JIRA_PROJECT_KEY=PROJ
EOF
```

**Replace with your actual values:**
- `your-company.atlassian.net` - Your Jira domain
- `your_api_key_here` - The API token you created
- `your-email@company.com` - Your Jira login email
- `PROJ` - Your Jira project key (usually 2-4 letters)

### 4. Configure Git and GitHub

Ensure your Git is configured for SSH access:

```bash
# Check Git configuration
git config --global user.name
git config --global user.email

# Test GitHub SSH access
ssh -T git@github.com
```

If SSH isn't set up, follow [GitHub's SSH key guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).

### 5. Configure Repository

Edit `real_development_workflow_by_id.py` to point to your repository:

```python
# Find this line and update it:
self.repo_url = "git@github.com:YourUsername/YourRepo.git"
```

Replace `YourUsername/YourRepo` with your actual GitHub repository.

## 🧪 Test Your Setup

### Quick Setup Verification

Run these commands to verify everything works:

```bash
# 1. Test Python environment
poetry run python -c "print('✅ Python environment works')"

# 2. Test Jira API connection
poetry run python -c "
from plugins.jira.api import JiraAPI
from plugins.jira.config import JiraConfig
config = JiraConfig.from_env()
if config:
    print('✅ Jira configuration loaded')
else:
    print('❌ Jira configuration missing')
"

# 3. Test Claude CLI
claude --print "Test successful"
```

### Test With a Real Task

1. **Find a Jira task ID** in your project (e.g., `PROJ-123`)
2. **Run the workflow** with a test task:

```bash
poetry run python real_development_workflow_by_id.py PROJ-123
```

3. **Expected behavior:**
   - Fetches task from Jira ✅
   - Moves task to In Progress ✅  
   - Clones repository to `./temp` ✅
   - Opens Terminal with Claude CLI ✅

4. **In the Terminal session:**
   - Work with Claude CLI
   - Create some test files
   - Exit Claude CLI (Ctrl+C)

5. **Auto-completion should:**
   - Create GitHub PR ✅
   - Update Jira task to Done ✅
   - Clean up `./temp` directory ✅

## 🎯 Your First Automated Development Session

### Example Workflow

Let's say you have task `PROJ-456` to "Add user authentication":

1. **Launch the workflow:**
   ```bash
   poetry run python real_development_workflow_by_id.py PROJ-456
   ```

2. **The system will:**
   - Fetch task details from Jira
   - Move task to "In Progress"
   - Clone your repository to `./temp`
   - Open Terminal with Claude CLI

3. **In the Terminal with Claude CLI:**
   ```
   > Help me implement user authentication for this project
   ```

4. **Work with Claude to:**
   - Analyze the codebase
   - Create authentication components
   - Add necessary dependencies
   - Write tests

5. **When finished, exit Claude CLI:**
   - Press `Ctrl+C` or type `exit`

6. **The system automatically:**
   - Commits your changes
   - Pushes to GitHub
   - Creates a pull request
   - Updates Jira task to Done
   - Cleans up temp files

## 🛠️ Troubleshooting

### Common Setup Issues

#### "Jira configuration not available"
- Check your `.env` file exists
- Verify all environment variables are set
- Test your API key in Jira web interface

#### "Claude CLI not found"
- Ensure Claude CLI is installed: `claude --version`
- Add Claude CLI to your PATH
- Restart your terminal after installation

#### "Repository clone failed"
- Test SSH access: `ssh -T git@github.com`
- Check repository URL in the code
- Verify you have access to the repository

#### "No Terminal window opens"
- Ensure you're on macOS (Terminal.app integration)
- Check Terminal app permissions
- Try running AppleScript manually

### Getting Help

If you encounter issues:

1. **Check the main README** for additional context
2. **Verify each prerequisite** is properly installed
3. **Test components individually** (Jira API, Claude CLI, Git)
4. **Check environment variables** are loaded correctly

## 🚀 Next Steps

Once your setup is working:

1. **Try with different task types** - See how Claude CLI handles various development tasks
2. **Customize branch naming** - Modify the branch naming pattern if needed
3. **Integrate with your team** - Share the setup process with team members
4. **Optimize your workflow** - Adjust timeouts and settings as needed

## 💡 Pro Tips

### Efficient Usage

- **Use descriptive Jira task summaries** - They become branch names and commit messages
- **Save files frequently** in the Claude CLI session - Changes are auto-detected
- **Work incrementally** - Exit and restart Claude CLI if sessions get too long
- **Review PRs promptly** - The system creates well-documented PRs ready for review

### Workflow Optimization  

- **Batch similar tasks** - Process multiple related tasks in sequence
- **Use consistent naming** - Maintain consistent Jira task naming for better automation
- **Monitor temp directory** - It should always be empty after completion
- **Check PR descriptions** - The system generates detailed PR descriptions automatically

You're now ready to use the AI Development Automation System! 🎉