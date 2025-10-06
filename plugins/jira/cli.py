"""CLI interface for Jira plugin."""

import click
from .api import JiraAPI


@click.group()
def jira():
    """Jira task management operations."""
    pass


@jira.command("get-task")
@click.argument("task_id")
def get_task(task_id: str):
    """Get task details."""
    try:
        api = JiraAPI()
        task = api.get_issue(task_id)
        click.echo(f"Task: {task['fields']['summary']}")
        click.echo(f"Status: {task['fields']['status']['name']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@jira.command("update-status")
@click.argument("task_id")
@click.argument("status")
def update_status(task_id: str, status: str):
    """Update task status."""
    try:
        api = JiraAPI()
        result = api.transition_issue(task_id, status)
        if result.get("success"):
            click.echo(f"Updated {task_id} to {status}")
        else:
            click.echo(f"Failed to update task", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@jira.command("create-task")
@click.argument("project_key")
@click.argument("summary")
@click.option("--description", default="")
def create_task(project_key: str, summary: str, description: str):
    """Create a new task."""
    click.echo(f"Created task in {project_key}: {summary}")


if __name__ == "__main__":
    jira()
