import unittest
import os
import shlex
import tempfile
import shutil
from io import StringIO
from unittest.mock import patch
from mackup.main import main
from mackup import utils


class TestCLI(unittest.TestCase):
    """Test suite for CLI commands: backup, restore, and copy mode workflows."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary directories for testing
        self.test_home = tempfile.mkdtemp(prefix="mackup_test_home_")
        self.test_storage = tempfile.mkdtemp(prefix="mackup_test_storage_")
        self.mackup_folder = os.path.join(self.test_storage, "Mackup")

        # Store original HOME
        self.original_home = os.environ.get("HOME")
        self.original_xdg = os.environ.get("XDG_CONFIG_HOME")

        # Set HOME to our test directory
        os.environ["HOME"] = self.test_home
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.test_home, ".config")

        # Create test config file
        self.config_path = os.path.join(self.test_home, ".mackup.cfg")
        with open(self.config_path, "w") as f:
            f.write("[storage]\n")
            f.write("engine = file_system\n")
            f.write(f"path = {self.test_storage}\n")
            f.write("directory = Mackup\n")
            f.write("\n")
            f.write("[applications_to_sync]\n")
            f.write("test-app\n")

        # Create a test application config in the apps database
        self.test_app_name = "test-app"
        self.test_file_name = ".testrc"
        self.test_file_path = os.path.join(self.test_home, self.test_file_name)

        # Create test file with content
        with open(self.test_file_path, "w") as f:
            f.write("test_config=value\n")

        # Create custom application config
        self.custom_apps_dir = os.path.join(self.test_home, ".mackup")
        os.makedirs(self.custom_apps_dir, exist_ok=True)

        self.custom_app_config = os.path.join(self.custom_apps_dir, "test-app.cfg")
        with open(self.custom_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {self.test_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{self.test_file_name}\n")

        # Force yes to all prompts
        utils.FORCE_YES = True
        utils.CAN_RUN_AS_ROOT = False

    def tearDown(self):
        """Clean up test environment after each test."""
        # Restore original HOME
        if self.original_home:
            os.environ["HOME"] = self.original_home
        else:
            os.environ.pop("HOME", None)

        # Restore original XDG_CONFIG_HOME
        if self.original_xdg:
            os.environ["XDG_CONFIG_HOME"] = self.original_xdg
        else:
            os.environ.pop("XDG_CONFIG_HOME", None)

        # Clean up temporary directories
        if os.path.exists(self.test_home):
            shutil.rmtree(self.test_home)
        if os.path.exists(self.test_storage):
            shutil.rmtree(self.test_storage)

        # Reset utils flags
        utils.FORCE_YES = False
        utils.CAN_RUN_AS_ROOT = False

    def run_cli(self, *args):
        """Run the CLI and capture stdout."""
        with patch("sys.argv", ["mackup", *args]):
            with patch("sys.stdout", new_callable=StringIO) as captured_output:
                main()
                return captured_output.getvalue()

    def test_backup_creates_mackup_folder(self):
        """Test that mackup backup creates the Mackup folder if it doesn't exist."""
        # Ensure Mackup folder doesn't exist
        self.assertFalse(os.path.exists(self.mackup_folder))

        # Mock sys.argv to simulate 'mackup backup'
        self.run_cli("backup")

        # Check that Mackup folder was created
        self.assertTrue(os.path.exists(self.mackup_folder))

    def test_backup_copies_file(self):
        """Test that mackup backup successfully copies a file to the backup location."""
        # Ensure test file exists
        self.assertTrue(os.path.exists(self.test_file_path))

        # Run backup
        self.run_cli("backup")

        # Check that file was copied to Mackup folder
        backed_up_file = os.path.join(self.mackup_folder, self.test_file_name)
        self.assertTrue(os.path.exists(backed_up_file))

        # Verify content is the same
        with open(self.test_file_path, "r") as f:
            original_content = f.read()
        with open(backed_up_file, "r") as f:
            backed_up_content = f.read()

        self.assertEqual(original_content, backed_up_content)

    def test_restore_copies_file_back(self):
        """Test that mackup restore successfully copies a file back from backup."""
        # First, create a backup
        self.run_cli("backup")

        # Verify backup exists
        backed_up_file = os.path.join(self.mackup_folder, self.test_file_name)
        self.assertTrue(os.path.exists(backed_up_file))

        # Remove original file
        os.remove(self.test_file_path)
        self.assertFalse(os.path.exists(self.test_file_path))

        # Run restore
        self.run_cli("restore")

        # Check that file was restored
        self.assertTrue(os.path.exists(self.test_file_path))

        # Verify content is correct
        with open(self.test_file_path, "r") as f:
            restored_content = f.read()

        self.assertEqual(restored_content, "test_config=value\n")

    def test_backup_and_restore_full_workflow(self):
        """Test complete backup and restore workflow."""
        original_content = "test_config=value\n"

        # Verify original file exists and has correct content
        self.assertTrue(os.path.exists(self.test_file_path))
        with open(self.test_file_path, "r") as f:
            self.assertEqual(f.read(), original_content)

        # Step 1: Backup
        self.run_cli("backup")

        # Verify backup was created
        backed_up_file = os.path.join(self.mackup_folder, self.test_file_name)
        self.assertTrue(os.path.exists(backed_up_file))

        # Step 2: Modify original file
        modified_content = "test_config=modified\n"
        with open(self.test_file_path, "w") as f:
            f.write(modified_content)

        # Verify file was modified
        with open(self.test_file_path, "r") as f:
            self.assertEqual(f.read(), modified_content)

        # Step 3: Restore (should replace modified file with backup)
        self.run_cli("restore")

        # Verify file was restored to original content
        with open(self.test_file_path, "r") as f:
            self.assertEqual(f.read(), original_content)

    def test_backup_preserves_file_permissions(self):
        """Test that mackup backup preserves file permissions."""
        # Set specific permissions on test file
        os.chmod(self.test_file_path, 0o600)

        # Run backup
        self.run_cli("backup")

        # Check backup file permissions
        backed_up_file = os.path.join(self.mackup_folder, self.test_file_name)
        self.assertTrue(os.path.exists(backed_up_file))

        # Verify permissions are preserved (mackup sets to 0600 by default)
        backed_up_stat = os.stat(backed_up_file)
        self.assertEqual(backed_up_stat.st_mode & 0o777, 0o600)

    def test_restore_with_missing_backup(self):
        """Test that mackup restore handles missing backup files gracefully."""
        # Ensure no backup exists
        self.assertFalse(os.path.exists(self.mackup_folder))

        # Create the mackup folder but don't add any files
        os.makedirs(self.mackup_folder, exist_ok=True)

        # Run restore (should not crash even though no backup exists)
        try:
            self.run_cli("restore")
            # If no exception is raised, the test passes
            # (restore should gracefully handle missing files)
        except Exception as e:
            self.fail(f"Restore raised an exception with missing backup: {e}")

    def test_backup_with_folder(self):
        """Test that mackup backup works with folders, not just files."""
        # Create a test folder with a file inside
        test_folder_name = ".test_folder"
        test_folder_path = os.path.join(self.test_home, test_folder_name)
        os.makedirs(test_folder_path, exist_ok=True)

        test_file_in_folder = os.path.join(test_folder_path, "config.txt")
        with open(test_file_in_folder, "w") as f:
            f.write("folder_config=value\n")

        # Update custom app config to include the folder
        with open(self.custom_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {self.test_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{self.test_file_name}\n")
            f.write(f"{test_folder_name}\n")

        # Run backup
        self.run_cli("backup")

        # Check that folder was copied
        backed_up_folder = os.path.join(self.mackup_folder, test_folder_name)
        self.assertTrue(os.path.exists(backed_up_folder))
        self.assertTrue(os.path.isdir(backed_up_folder))

        # Check that file inside folder was copied
        backed_up_file_in_folder = os.path.join(backed_up_folder, "config.txt")
        self.assertTrue(os.path.exists(backed_up_file_in_folder))

        # Verify content
        with open(backed_up_file_in_folder, "r") as f:
            self.assertEqual(f.read(), "folder_config=value\n")

    def test_restore_with_folder(self):
        """Test that mackup restore works with folders."""
        # Create a test folder with a file inside
        test_folder_name = ".test_folder"
        test_folder_path = os.path.join(self.test_home, test_folder_name)
        os.makedirs(test_folder_path, exist_ok=True)

        test_file_in_folder = os.path.join(test_folder_path, "config.txt")
        with open(test_file_in_folder, "w") as f:
            f.write("folder_config=value\n")

        # Update custom app config to include the folder
        with open(self.custom_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {self.test_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{self.test_file_name}\n")
            f.write(f"{test_folder_name}\n")

        # Run backup first
        self.run_cli("backup")

        # Delete the folder
        shutil.rmtree(test_folder_path)
        self.assertFalse(os.path.exists(test_folder_path))

        # Run restore
        self.run_cli("restore")

        # Check that folder was restored
        self.assertTrue(os.path.exists(test_folder_path))
        self.assertTrue(os.path.isdir(test_folder_path))

        # Check that file inside folder was restored
        self.assertTrue(os.path.exists(test_file_in_folder))

        # Verify content
        with open(test_file_in_folder, "r") as f:
            self.assertEqual(f.read(), "folder_config=value\n")

    def test_diff_reports_identical_file_when_requested(self):
        """Test that diff can report identical files when filtered explicitly."""
        self.run_cli("backup")

        output = self.run_cli("diff", "--status=identical")

        self.assertIn("Application", output)
        self.assertIn("Path", output)
        self.assertIn("Status", output)
        self.assertIn(self.test_app_name, output)
        self.assertIn(self.test_file_name, output)
        self.assertIn("identical", output)

    def test_diff_reports_modified_local_file(self):
        """Test that diff reports different when local file content changes."""
        self.run_cli("backup")

        with open(self.test_file_path, "w") as f:
            f.write("test_config=modified\n")

        output = self.run_cli("diff")

        self.assertIn(self.test_file_name, output)
        self.assertIn("different", output)

    def test_diff_defaults_to_different_status(self):
        """Test that diff shows only different rows by default."""
        self.run_cli("backup")

        extra_file_name = ".extra"
        extra_file_path = os.path.join(self.test_home, extra_file_name)
        with open(extra_file_path, "w") as f:
            f.write("extra=value\n")

        with open(self.custom_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {self.test_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{self.test_file_name}\n")
            f.write(f"{extra_file_name}\n")

        with open(self.test_file_path, "w") as f:
            f.write("test_config=modified\n")

        output = self.run_cli("diff")

        self.assertIn(self.test_file_name, output)
        self.assertIn("different", output)
        self.assertNotIn(extra_file_name, output)
        self.assertNotIn("missing_backup", output)
        self.assertNotIn("identical", output)

    def test_diff_reports_missing_local_file_when_requested(self):
        """Test that diff can report missing_local when filtered explicitly."""
        self.run_cli("backup")
        os.remove(self.test_file_path)

        output = self.run_cli("diff", "--status=missing_local")

        self.assertIn(self.test_file_name, output)
        self.assertIn("missing_local", output)

    def test_diff_reports_missing_backup_file_when_requested(self):
        """Test that diff can report missing_backup when filtered explicitly."""
        self.run_cli("backup")
        os.remove(os.path.join(self.mackup_folder, self.test_file_name))

        output = self.run_cli("diff", "--status=missing_backup")

        self.assertIn(self.test_file_name, output)
        self.assertIn("missing_backup", output)

    def test_diff_reports_directory_differences(self):
        """Test that diff compares directories and reports differences."""
        test_folder_name = ".test_folder"
        test_folder_path = os.path.join(self.test_home, test_folder_name)
        os.makedirs(test_folder_path, exist_ok=True)

        test_file_in_folder = os.path.join(test_folder_path, "config.txt")
        with open(test_file_in_folder, "w") as f:
            f.write("folder_config=value\n")

        with open(self.custom_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {self.test_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{self.test_file_name}\n")
            f.write(f"{test_folder_name}\n")

        self.run_cli("backup")

        with open(test_file_in_folder, "w") as f:
            f.write("folder_config=modified\n")

        output = self.run_cli("diff")

        self.assertIn(test_folder_name, output)
        self.assertIn("different", output)

    def test_diff_filters_rows_by_status(self):
        """Test that diff can filter output to a single status."""
        self.run_cli("backup")

        with open(self.test_file_path, "w") as f:
            f.write("test_config=modified\n")

        extra_file_name = ".extra"
        extra_file_path = os.path.join(self.test_home, extra_file_name)
        with open(extra_file_path, "w") as f:
            f.write("extra=value\n")

        with open(self.custom_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {self.test_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{self.test_file_name}\n")
            f.write(f"{extra_file_name}\n")

        output = self.run_cli("diff", "--status=different")

        self.assertIn(self.test_file_name, output)
        self.assertIn("different", output)
        self.assertNotIn(extra_file_name, output)
        self.assertNotIn("missing_backup", output)

    def test_diff_reports_when_status_filter_has_no_matches(self):
        """Test that diff reports empty results when no rows match a status filter."""
        self.run_cli("backup")

        output = self.run_cli("diff", "--status=different")

        self.assertEqual(output.strip(), "No managed configuration paths found for status: different.")

    def test_bcomp_uses_configured_backup_root(self):
        """Test that bcomp uses the configured Mackup folder by default."""
        with patch("mackup.application.subprocess.run") as mock_run:
            self.run_cli("bcomp", self.test_app_name)

        expected_command = "bcomp '{}' '{}'".format(
            self.test_file_path, os.path.join(self.mackup_folder, self.test_file_name)
        )
        mock_run.assert_called_once_with(["bash", "-lc", expected_command], check=False)

    def test_bcomp_uses_override_backup_root(self):
        """Test that bcomp can use an explicit backup root override."""
        override_root = "~/CustomMackup"
        expanded_override = os.path.expanduser(override_root)

        with patch("mackup.application.subprocess.run") as mock_run:
            self.run_cli("bcomp", self.test_app_name, f"--backup-root={override_root}")

        expected_command = "bcomp '{}' '{}'".format(
            self.test_file_path, os.path.join(expanded_override, self.test_file_name)
        )
        mock_run.assert_called_once_with(["bash", "-lc", expected_command], check=False)

    def test_bcomp_all_uses_only_different_paths(self):
        """Test that batch bcomp stages only rows matching the default different status."""
        second_app_name = "second-app"
        second_file_name = ".secondrc"
        second_file_path = os.path.join(self.test_home, second_file_name)
        second_app_config = os.path.join(self.custom_apps_dir, "second-app.cfg")

        with open(self.config_path, "a") as f:
            f.write(f"{second_app_name}\n")

        with open(second_file_path, "w") as f:
            f.write("second=value\n")

        with open(second_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {second_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{second_file_name}\n")

        self.run_cli("backup")

        with open(self.test_file_path, "w") as f:
            f.write("test_config=modified\n")

        def assert_bcomp_tree(args, check):
            self.assertFalse(check)
            self.assertEqual(args[0:2], ["bash", "-lc"])
            command_parts = shlex.split(args[2])
            self.assertEqual(command_parts[0], "bcomp")
            self.assertEqual(len(command_parts), 3)
            local_root, backup_root = command_parts[1], command_parts[2]

            staged_local = os.path.join(local_root, self.test_file_name)
            staged_backup = os.path.join(backup_root, self.test_file_name)
            self.assertTrue(os.path.exists(staged_local))
            self.assertTrue(os.path.exists(staged_backup))
            self.assertFalse(os.path.islink(staged_local))
            self.assertFalse(os.path.islink(staged_backup))
            self.assertTrue(os.path.samefile(staged_local, self.test_file_path))
            self.assertTrue(
                os.path.samefile(
                    staged_backup, os.path.join(self.mackup_folder, self.test_file_name)
                )
            )
            self.assertFalse(os.path.exists(os.path.join(local_root, second_file_name)))
            self.assertFalse(os.path.exists(os.path.join(backup_root, second_file_name)))

        with patch("mackup.utils.subprocess.run", side_effect=assert_bcomp_tree) as mock_run:
            self.run_cli("bcomp", "--all")

        mock_run.assert_called_once()

    def test_bcomp_all_reports_when_no_different_paths_exist(self):
        """Test that batch bcomp reports no matches and does not launch bcomp."""
        self.run_cli("backup")

        with patch("mackup.utils.subprocess.run") as mock_run:
            output = self.run_cli("bcomp", "--all")

        mock_run.assert_not_called()
        self.assertEqual(output.strip(), "No managed configuration paths found for status: different.")

    def test_bcomp_all_handles_directory_paths_with_trailing_slash(self):
        """Test that batch bcomp normalizes trailing slashes on directory entries."""
        test_folder_name = ".test_folder/"
        normalized_folder_name = ".test_folder"
        test_folder_path = os.path.join(self.test_home, normalized_folder_name)
        os.makedirs(test_folder_path, exist_ok=True)

        test_file_in_folder = os.path.join(test_folder_path, "config.txt")
        with open(test_file_in_folder, "w") as f:
            f.write("folder_config=value\n")

        with open(self.custom_app_config, "w") as f:
            f.write("[application]\n")
            f.write(f"name = {self.test_app_name}\n")
            f.write("\n")
            f.write("[configuration_files]\n")
            f.write(f"{test_folder_name}\n")

        self.run_cli("backup")

        with open(test_file_in_folder, "w") as f:
            f.write("folder_config=modified\n")

        def assert_bcomp_tree(args, check):
            self.assertFalse(check)
            command_parts = shlex.split(args[2])
            local_root, backup_root = command_parts[1], command_parts[2]
            staged_local_dir = os.path.join(local_root, normalized_folder_name)
            staged_backup_dir = os.path.join(backup_root, normalized_folder_name)
            self.assertTrue(os.path.isdir(staged_local_dir))
            self.assertTrue(os.path.isdir(staged_backup_dir))
            self.assertFalse(os.path.islink(staged_local_dir))
            self.assertFalse(os.path.islink(staged_backup_dir))
            self.assertTrue(
                os.path.samefile(
                    os.path.join(staged_local_dir, "config.txt"), test_file_in_folder
                )
            )
            self.assertTrue(
                os.path.samefile(
                    os.path.join(staged_backup_dir, "config.txt"),
                    os.path.join(self.mackup_folder, normalized_folder_name, "config.txt"),
                )
            )

        with patch("mackup.utils.subprocess.run", side_effect=assert_bcomp_tree):
            self.run_cli("bcomp", "--all")


if __name__ == "__main__":
    unittest.main()
