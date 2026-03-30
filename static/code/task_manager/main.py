"""
Task Manager CLI - Main Entry Point
A command-line task management tool with persistent storage.
"""
import argparse
import sys
from storage import TaskStorage


def main():
    parser = argparse.ArgumentParser(
        description="Task Manager - manage your tasks from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  task add "Buy groceries" --tag personal --priority high
  task list --status pending --tag work
  task done 3
  task remove 5
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Add task
    add_parser = subparsers.add_parser('add', help='Add a new task')
    add_parser.add_argument('title', help='Task title')
    add_parser.add_argument('--tag', '-t', action='append', default=[], help='Tag (repeatable)')
    add_parser.add_argument('--priority', '-p', choices=['low', 'medium', 'high'], default='medium')
    add_parser.add_argument('--notes', '-n', default='', help='Optional notes')

    # List tasks
    list_parser = subparsers.add_parser('list', help='List tasks')
    list_parser.add_argument('--status', choices=['pending', 'done', 'all'], default='pending')
    list_parser.add_argument('--tag', '-t', help='Filter by tag')
    list_parser.add_argument('--priority', '-p', choices=['low', 'medium', 'high'])
    list_parser.add_argument('--sort', choices=['priority', 'created', 'title'], default='created')

    # Mark done
    done_parser = subparsers.add_parser('done', help='Mark a task as done')
    done_parser.add_argument('id', type=int, help='Task ID')

    # Remove task
    remove_parser = subparsers.add_parser('remove', help='Remove a task')
    remove_parser.add_argument('id', type=int, help='Task ID')

    # Show task details
    show_parser = subparsers.add_parser('show', help='Show task details')
    show_parser.add_argument('id', type=int, help='Task ID')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    storage = TaskStorage()

    if args.command == 'add':
        task = storage.add_task(
            title=args.title,
            tags=args.tag,
            priority=args.priority,
            notes=args.notes,
        )
        print(f"✓ Added task #{task['id']}: {task['title']}")

    elif args.command == 'list':
        tasks = storage.list_tasks(
            status=args.status,
            tag=args.tag,
            priority=args.priority,
            sort_by=args.sort,
        )
        if not tasks:
            print("No tasks found.")
        else:
            print_tasks(tasks)

    elif args.command == 'done':
        task = storage.mark_done(args.id)
        if task:
            print(f"✓ Marked task #{args.id} as done: {task['title']}")
        else:
            print(f"Error: Task #{args.id} not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'remove':
        if storage.remove_task(args.id):
            print(f"✓ Removed task #{args.id}")
        else:
            print(f"Error: Task #{args.id} not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'show':
        task = storage.get_task(args.id)
        if task:
            print_task_detail(task)
        else:
            print(f"Error: Task #{args.id} not found.", file=sys.stderr)
            sys.exit(1)


PRIORITY_ORDER = {'high': 0, 'medium': 1, 'low': 2}
PRIORITY_ICONS = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
STATUS_ICONS = {'pending': '○', 'done': '✓'}


def print_tasks(tasks: list) -> None:
    """Print a formatted list of tasks."""
    print(f"\n{'ID':<5} {'P':<3} {'S':<3} {'Title':<40} {'Tags'}")
    print("-" * 70)
    for task in tasks:
        icon = PRIORITY_ICONS.get(task['priority'], ' ')
        status = STATUS_ICONS.get(task['status'], '?')
        tags = ', '.join(task.get('tags', [])) or '-'
        title = task['title'][:38] + '..' if len(task['title']) > 40 else task['title']
        print(f"#{task['id']:<4} {icon:<3} {status:<3} {title:<40} {tags}")
    print()


def print_task_detail(task: dict) -> None:
    """Print detailed info about a single task."""
    print(f"\nTask #{task['id']}")
    print(f"  Title:    {task['title']}")
    print(f"  Status:   {task['status']}")
    print(f"  Priority: {task['priority']}")
    print(f"  Tags:     {', '.join(task.get('tags', [])) or 'none'}")
    print(f"  Created:  {task.get('created_at', 'unknown')}")
    if task.get('notes'):
        print(f"  Notes:    {task['notes']}")
    print()


if __name__ == '__main__':
    main()
