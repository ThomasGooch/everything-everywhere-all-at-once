"""CLI interface for Confluence plugin."""

import click

from .api import ConfluenceAPI
from .tools import ConfluenceTools


@click.group()
def confluence() -> None:
    """Confluence documentation operations."""
    pass


@confluence.command("create-page")
@click.argument("title")
@click.argument("content")
@click.option("--space-key", help="Confluence space key")
@click.option("--parent-id", help="Parent page ID")
def create_page(title: str, content: str, space_key: str, parent_id: str) -> None:
    """Create a new Confluence page."""
    try:
        api = ConfluenceAPI()
        result = api.create_page(title, content, space_key, parent_id)
        if result.get("success"):
            click.echo(f"✅ Created page: {title}")
            click.echo(f"📄 URL: {result['page_url']}")
        else:
            click.echo(f"❌ Failed to create page: {result.get('error')}", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@confluence.command("search-pages")
@click.argument("query")
@click.option("--limit", default=10, help="Maximum number of results")
def search_pages(query: str, limit: int) -> None:
    """Search for Confluence pages using CQL."""
    try:
        api = ConfluenceAPI()
        result = api.search_pages(query, limit)
        if result.get("success"):
            pages = result["results"]
            click.echo(f"Found {len(pages)} pages:")
            for page in pages:
                click.echo(f"📄 {page['title']} (ID: {page['id']})")
        else:
            click.echo(f"❌ Search failed: {result.get('error')}", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@confluence.command("create-task-doc")
@click.argument("task_id")
@click.option("--pr-url", help="Pull request URL")
@click.option("--notes", help="Completion notes")
@click.option("--space-key", help="Confluence space key")
def create_task_doc(task_id: str, pr_url: str, notes: str, space_key: str) -> None:
    """Create documentation for a completed task."""
    try:
        # This would need Jira integration to get task details
        # For now, create a simple documentation structure
        tools = ConfluenceTools()

        # Mock task details for CLI usage
        task_details = {
            "fields": {
                "summary": f"Task {task_id}",
                "description": "Task completed via CLI",
                "status": {"name": "Done"},
                "assignee": {"displayName": "CLI User"},
            },
            "self": f"https://company.atlassian.net/browse/{task_id}",
        }

        result = tools.create_task_documentation(
            task_id, task_details, pr_url, notes, space_key
        )

        if result.get("success"):
            action = result.get("action", "created")
            click.echo(f"✅ {action.title()} documentation for {task_id}")
            click.echo(f"📄 URL: {result['page_url']}")
        else:
            click.echo(
                f"❌ Failed to create documentation: {result.get('error')}", err=True
            )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@confluence.command("create-project-doc")
@click.argument("project_key")
@click.argument("project_name")
@click.option("--space-key", help="Confluence space key")
def create_project_doc(project_key: str, project_name: str, space_key: str) -> None:
    """Create project overview documentation."""
    try:
        tools = ConfluenceTools()
        result = tools.create_project_documentation(
            project_key, project_name, space_key
        )

        if result.get("success"):
            click.echo(f"✅ Created project documentation: {project_name}")
            click.echo(f"📄 URL: {result['page_url']}")
        else:
            click.echo(
                f"❌ Failed to create project documentation: {result.get('error')}",
                err=True,
            )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@confluence.command("space-info")
def space_info() -> None:
    """Show Confluence space configuration."""
    try:
        tools = ConfluenceTools()
        info = tools.get_space_info()

        click.echo("Confluence Configuration:")
        click.echo(f"📍 Base URL: {info['base_url']}")
        click.echo(f"🏠 Space Key: {info['space_key']}")
        click.echo(f"👤 Username: {info['username']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    confluence()
