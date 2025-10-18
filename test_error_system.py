#!/usr/bin/env python3
"""
Test script for telegram bot error reporting system

Usage: python test_error_system.py
"""

import os
import sys
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_sqlite import Database
from config_local import DEVELOPER_CHAT_ID, ENABLE_DEVELOPER_NOTIFICATIONS, OPENAI_API_KEY, ENABLE_AI_ERROR_PROCESSING

class ErrorSystemTester:
    """Class for testing error reporting system"""

    def __init__(self):
        self.db = None
        self.test_results = []
        self.start_time = datetime.now()

    def log(self, message, status="INFO"):
        """Log test results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icons = {
            "SUCCESS": "[OK]",
            "ERROR": "[FAIL]",
            "WARNING": "[WARN]",
            "INFO": "[INFO]"
        }
        icon = status_icons.get(status, "[INFO]")
        print(f"[{timestamp}] {icon} {message}")
        self.test_results.append({
            'timestamp': timestamp,
            'status': status,
            'message': message
        })

    def print_header(self, title):
        """Print test header"""
        print(f"\n{'='*60}")
        print(f"[TEST] {title}")
        print(f"{'='*60}")

    def test_database_connection(self):
        """Test database connection"""
        self.print_header("TESTING DATABASE CONNECTION")

        try:
            self.db = Database()
            if self.db.connection:
                self.log("Database connection established successfully", "SUCCESS")
                return True
            else:
                self.log("Failed to connect to database", "ERROR")
                return False
        except Exception as e:
            self.log(f"Database connection error: {e}", "ERROR")
            return False

    def test_table_creation(self):
        """Test table creation"""
        self.print_header("TESTING TABLE CREATION")

        try:
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='errors'")

            if cursor.fetchone():
                self.log("Table 'errors' exists", "SUCCESS")
                return True
            else:
                self.log("Table 'errors' not found", "ERROR")
                return False
        except Exception as e:
            self.log(f"Table check error: {e}", "ERROR")
            return False

    def test_add_error(self):
        """Test adding error to database"""
        self.print_header("TESTING ADD ERROR")

        try:
            error_id = self.db.add_error(
                admin_id=123456789,
                error_type="bug",
                title="Test error for system validation",
                description="This is a test error created by testing script",
                priority="medium"
            )

            if error_id and error_id > 0:
                self.log(f"Error successfully added with ID: {error_id}", "SUCCESS")
                return error_id
            else:
                self.log("Failed to add error", "ERROR")
                return None
        except Exception as e:
            self.log(f"Error adding error: {e}", "ERROR")
            return None

    def test_get_errors(self):
        """Test getting errors list"""
        self.print_header("TESTING GET ERRORS")

        try:
            errors = self.db.get_errors(limit=10)

            if isinstance(errors, list) and len(errors) > 0:
                self.log(f"Retrieved {len(errors)} errors from database", "SUCCESS")

                first_error = errors[0]
                expected_fields = 14

                if len(first_error) == expected_fields:
                    self.log("Error data structure is correct", "SUCCESS")
                    return True
                else:
                    self.log(f"Wrong number of fields: expected {expected_fields}, got {len(first_error)}", "ERROR")
                    return False
            else:
                self.log("No errors found (this may be normal for new DB)", "WARNING")
                return True
        except Exception as e:
            self.log(f"Error getting errors: {e}", "ERROR")
            return False

    def test_ai_analysis_mock(self):
        """Test AI analysis (mock version)"""
        self.print_header("TESTING AI ANALYSIS")

        try:
            from bot import TelegramBot
            bot = TelegramBot()

            if not OPENAI_API_KEY or OPENAI_API_KEY == "ВСТАВЬТЕ_ВАШ_OPENAI_API_КЛЮЧ_ЗДЕСЬ":
                self.log("OpenAI API key not configured - skipping real analysis test", "WARNING")

                if hasattr(bot, 'process_error_with_ai'):
                    self.log("Method process_error_with_ai exists", "SUCCESS")
                    return True
                else:
                    self.log("Method process_error_with_ai not found", "ERROR")
                    return False
            else:
                self.log("OpenAI API key configured - can test real analysis", "SUCCESS")
                return True

        except ImportError as e:
            self.log(f"Bot import error: {e}", "ERROR")
            return False
        except Exception as e:
            self.log(f"AI analysis test error: {e}", "ERROR")
            return False

    def test_todo_integration(self):
        """Test TODO integration"""
        self.print_header("TESTING TODO INTEGRATION")

        try:
            from bot import TelegramBot
            bot = TelegramBot()

            if hasattr(bot, 'add_error_to_todo_file'):
                test_error_id = self.db.add_error(
                    admin_id=123456789,
                    error_type="improvement",
                    title="Test task for TODO",
                    description="This task created by test script",
                    priority="low"
                )

                if test_error_id:
                    success = bot.add_error_to_todo_file(
                        error_id=test_error_id,
                        title="Test task for TODO",
                        error_type="improvement",
                        priority="low",
                        ai_analysis="Test analysis for integration check"
                    )

                    if success:
                        self.log(f"Test error #{test_error_id} added to TODO file", "SUCCESS")

                        if os.path.exists('TODO.md'):
                            self.log("TODO.md file exists and accessible", "SUCCESS")
                            return True
                        else:
                            self.log("TODO.md file not found", "ERROR")
                            return False
                    else:
                        self.log("Failed to add error to TODO file", "ERROR")
                        return False
                else:
                    self.log("Failed to create test error for TODO", "ERROR")
                    return False
            else:
                self.log("Method add_error_to_todo_file not found", "ERROR")
                return False

        except Exception as e:
            self.log(f"TODO integration test error: {e}", "ERROR")
            return False

    def test_notification_system(self):
        """Test notification system"""
        self.print_header("TESTING NOTIFICATION SYSTEM")

        try:
            from bot import TelegramBot
            bot = TelegramBot()

            if hasattr(bot, 'send_developer_notification'):
                self.log("Method send_developer_notification exists", "SUCCESS")

                if ENABLE_DEVELOPER_NOTIFICATIONS:
                    self.log("Developer notifications enabled", "SUCCESS")
                else:
                    self.log("Developer notifications disabled", "WARNING")

                if DEVELOPER_CHAT_ID:
                    self.log(f"Developer chat ID configured: {DEVELOPER_CHAT_ID}", "SUCCESS")
                else:
                    self.log("Developer chat ID not configured", "WARNING")

                return True
            else:
                self.log("Method send_developer_notification not found", "ERROR")
                return False

        except Exception as e:
            self.log(f"Notification system test error: {e}", "ERROR")
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("STARTING ERROR REPORTING SYSTEM TESTS")
        print(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        tests = [
            ("Database Connection", self.test_database_connection),
            ("Table Creation", self.test_table_creation),
            ("Add Error", self.test_add_error),
            ("Get Errors", self.test_get_errors),
            ("AI Analysis", self.test_ai_analysis_mock),
            ("TODO Integration", self.test_todo_integration),
            ("Notification System", self.test_notification_system),
        ]

        passed = 0
        failed = 0
        warnings = 0

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Critical error in test '{test_name}': {e}", "ERROR")
                failed += 1

            time.sleep(0.5)

        self.print_summary(passed, failed, warnings)
        return failed == 0

    def print_summary(self, passed, failed, warnings):
        """Print test summary"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        print(f"\n{'='*80}")
        print("TEST RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"[OK] Passed: {passed}")
        print(f"[FAIL] Failed: {failed}")
        print(f"[WARN] Warnings: {warnings}")
        print(f"[%] Success rate: {((passed) / (passed + failed) * 100):.1f}%" if (passed + failed) > 0 else "N/A")

        print("\nDETAILED RESULTS:")
        for result in self.test_results:
            print(f"  [{result['timestamp']}] {result['status']}: {result['message']}")

        if failed == 0:
            print("\n*** ALL TESTS PASSED! ***")
            print("Error reporting system is ready to use.")
        else:
            print(f"\n*** SOME TESTS FAILED ({failed} out of {passed + failed}) ***")
            print("Check configuration and run tests again.")

        print(f"{'='*80}")

    def cleanup_test_data(self):
        """Cleanup test data"""
        self.print_header("CLEANUP TEST DATA")

        try:
            if self.db and self.db.connection:
                cursor = self.db.connection.cursor()
                cursor.execute("DELETE FROM errors WHERE title LIKE '%Test%' OR title LIKE '%test%'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='errors'")
                self.db.connection.commit()
                self.log("Test data cleaned", "SUCCESS")

        except Exception as e:
            self.log(f"Error during test data cleanup: {e}", "WARNING")

def main():
    """Main function"""
    print("TELEGRAM BOT ERROR SYSTEM TESTING")
    print("=" * 80)

    tester = ErrorSystemTester()

    try:
        success = tester.run_all_tests()
        tester.cleanup_test_data()

        exit_code = 0 if success else 1
        print(f"\nTest completed with exit code: {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        tester.cleanup_test_data()
        sys.exit(130)
    except Exception as e:
        print(f"\nCritical error during testing: {e}")
        tester.cleanup_test_data()
        sys.exit(1)

if __name__ == "__main__":
    main()