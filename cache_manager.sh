#!/bin/bash

# Cache management helper script for the social media platform

cd "$(dirname "$0")"

show_help() {
    echo "Cache Management Helper"
    echo "======================"
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  check [USER_ID]     Check cache for all users or specific user"
    echo "  clear [USER_ID]     Clear cache for all users or specific user"
    echo "  refresh USER_ID     Force refresh cache for specific user"
    echo "  stats               Show cache statistics"
    echo "  test USER_ID        Test cache operations for specific user"
    echo "  django              Use Django management command interface"
    echo
    echo "Examples:"
    echo "  $0 check           # Check cache for all users"
    echo "  $0 check 1         # Check cache for user ID 1"
    echo "  $0 clear           # Clear all user cache"
    echo "  $0 clear 1         # Clear cache for user ID 1"
    echo "  $0 refresh 1       # Force refresh cache for user ID 1"
    echo "  $0 stats           # Show cache statistics"
    echo "  $0 test 1          # Test cache operations for user ID 1"
    echo
}

case "$1" in
    "check")
        if [ -n "$2" ]; then
            echo "Checking cache for user ID: $2"
            python check_cache.py --user-id "$2"
        else
            echo "Checking cache for all users..."
            python check_cache.py
        fi
        ;;
    "clear")
        if [ -n "$2" ]; then
            echo "Clearing cache for user ID: $2"
            python manage.py check_user_cache --user-id "$2" --clear
        else
            echo "Clearing cache for all users..."
            python check_cache.py --clear-all
        fi
        ;;
    "refresh")
        if [ -n "$2" ]; then
            echo "Force refreshing cache for user ID: $2"
            python manage.py check_user_cache --user-id "$2" --refresh
        else
            echo "Error: User ID required for refresh operation"
            exit 1
        fi
        ;;
    "stats")
        echo "Showing cache statistics..."
        python manage.py check_user_cache --stats
        ;;
    "test")
        if [ -n "$2" ]; then
            echo "Testing cache operations for user ID: $2"
            python check_cache.py --user-id "$2" --test
        else
            echo "Error: User ID required for test operation"
            exit 1
        fi
        ;;
    "django")
        shift
        python manage.py check_user_cache "$@"
        ;;
    "help"|"-h"|"--help"|"")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac
