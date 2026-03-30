"""System static utilities being used by the modules."""

import base64
import filecmp
import os
import platform
import shutil
import stat
import subprocess
import sys
import sqlite3
import tempfile
from typing import Dict, List, NoReturn, Optional, Sequence

from . import constants


# Flag that controls how user confirmation works.
# If True, the user wants to say "yes" to everything.
FORCE_YES: bool = False
# If True, the user wants to say "no" to everything.
FORCE_NO: bool = False

# Flag that control if mackup can be run as root
CAN_RUN_AS_ROOT: bool = False


def confirm(question: str) -> bool:
    """
    Ask the user if he really wants something to happen.

    Args:
        question(str): What can happen

    Returns:
        (boolean): Confirmed or not
    """
    if FORCE_YES:
        return True
    if FORCE_NO:
        return False

    while True:
        answer: str = input(question + " <Enter|Yes|No> ").lower()

        if answer == "" or answer == "yes" or answer == "y":
            confirmed: bool = True
            break
        if answer == "no" or answer == "n":
            confirmed = False
            break

    return confirmed


def delete(filepath: str) -> None:
    """
    Delete the given file, directory or link.

    It Should support undelete later on.

    Args:
        filepath (str): Absolute full path to a file. e.g. /path/to/file
    """
    # Some files have ACLs, let's remove them recursively
    remove_acl(filepath)

    # Some files have immutable attributes, let's remove them recursively
    remove_immutable_attribute(filepath)

    # Finally remove the files and folders
    if os.path.isfile(filepath) or os.path.islink(filepath):
        os.remove(filepath)
    elif os.path.isdir(filepath):
        shutil.rmtree(filepath)


def copy(src: str, dst: str) -> None:
    """
    Copy a file or a folder (recursively) from src to dst.

    For the sake of simplicity, both src and dst must be absolute path and must
    include the filename of the file or folder.
    Also do not include any trailing slash.

    e.g. copy('/path/to/src_file', '/path/to/dst_file')
    or copy('/path/to/src_folder', '/path/to/dst_folder')

    But not: copy('/path/to/src_file', 'path/to/')
    or copy('/path/to/src_folder/', '/path/to/dst_folder')

    Args:
        src (str): Source file or folder
        dst (str): Destination file or folder
    """
    assert isinstance(src, str)
    assert os.path.exists(src)
    assert isinstance(dst, str)

    # Create the path to the dst file if it does not exist
    abs_path = os.path.dirname(os.path.abspath(dst))
    if not os.path.isdir(abs_path):
        os.makedirs(abs_path)

    # We need to copy a single file
    if os.path.isfile(src):
        # Copy the src file to dst
        shutil.copy(src, dst)

    # We need to copy a whole folder
    elif os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=shutil.copy)

    # What the heck is this?
    else:
        raise ValueError("Unsupported file: {}".format(src))

    # Set the good mode to the file or folder recursively
    chmod(dst)


def link(target: str, link_to: str) -> None:
    """
    Create a link to a target file or a folder.

    For the sake of simplicity, both target and link_to must be absolute path and must
    include the filename of the file or folder.
    Also do not include any trailing slash.

    e.g. link('/path/to/file', '/path/to/link')

    But not: link('/path/to/file', 'path/to/')
    or link('/path/to/folder/', '/path/to/link')

    Args:
        target (str): file or folder the link will point to
        link_to (str): Link to create
    """
    assert isinstance(target, str)
    assert os.path.exists(target)
    assert isinstance(link_to, str)

    # Create the path to the link if it does not exist
    abs_path = os.path.dirname(os.path.abspath(link_to))
    if not os.path.isdir(abs_path):
        os.makedirs(abs_path)

    # Make sure the file or folder recursively has the good mode
    chmod(target)

    # Create the link to target
    os.symlink(target, link_to)


def chmod(target: str) -> None:
    """
    Recursively set the chmod for files to 0600 and 0700 for folders.

    It's ok unless we need something more specific.

    Args:
        target (str): Root file or folder
    """
    assert isinstance(target, str)
    assert os.path.exists(target)

    file_mode = stat.S_IRUSR | stat.S_IWUSR
    folder_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR

    # Remove the immutable attribute recursively if there is one
    remove_immutable_attribute(target)

    if os.path.isfile(target):
        os.chmod(target, file_mode)

    elif os.path.isdir(target):
        # chmod the root item
        os.chmod(target, folder_mode)

        # chmod recursively in the folder it it's one
        for root, dirs, files in os.walk(target):
            for cur_dir in dirs:
                os.chmod(os.path.join(root, cur_dir), folder_mode)
            for cur_file in files:
                os.chmod(os.path.join(root, cur_file), file_mode)

    else:
        raise ValueError("Unsupported file type: {}".format(target))


def error(message: str) -> NoReturn:
    """
    Throw an error with the given message and immediately quit.

    Args:
        message(str): The message to display.
    """
    fail: str = "\033[91m"
    end: str = "\033[0m"
    sys.exit(fail + "Error: {}".format(message) + end)


def get_dropbox_folder_location() -> str:
    """
    Try to locate the Dropbox folder.

    Returns:
        (str) Full path to the current Dropbox folder
    """
    host_db_path = os.path.join(os.environ["HOME"], ".dropbox/host.db")
    try:
        with open(host_db_path, "r") as f_hostdb:
            data = f_hostdb.read().split()
    except IOError:
        error(constants.ERROR_UNABLE_TO_FIND_STORAGE.format(provider="Dropbox install"))
    dropbox_home = base64.b64decode(data[1]).decode()

    return dropbox_home


def get_google_drive_folder_location() -> str:
    """
    Try to locate the Google Drive folder.

    Returns:
        (str) Full path to the current Google Drive folder
    """
    gdrive_db_path = "Library/Application Support/Google/Drive/sync_config.db"
    yosemite_gdrive_db_path = (
        "Library/Application Support/Google/Drive/" "user_default/sync_config.db"
    )
    yosemite_gdrive_db = os.path.join(os.environ["HOME"], yosemite_gdrive_db_path)
    if os.path.isfile(yosemite_gdrive_db):
        gdrive_db_path = yosemite_gdrive_db

    googledrive_home: Optional[str] = None

    gdrive_db = os.path.join(os.environ["HOME"], gdrive_db_path)
    if os.path.isfile(gdrive_db):
        con = sqlite3.connect(gdrive_db)
        if con:
            cur = con.cursor()
            query = (
                "SELECT data_value "
                "FROM data "
                "WHERE entry_key = 'local_sync_root_path';"
            )
            cur.execute(query)
            data = cur.fetchone()
            googledrive_home = str(data[0])
            con.close()

    if not googledrive_home:
        error(
            constants.ERROR_UNABLE_TO_FIND_STORAGE.format(
                provider="Google Drive install"
            )
        )

    return googledrive_home


def get_icloud_folder_location() -> str:
    """
    Try to locate the iCloud Drive folder.

    Returns:
        (str) Full path to the iCloud Drive folder.
    """
    yosemite_icloud_path = "~/Library/Mobile Documents/com~apple~CloudDocs/"

    icloud_home = os.path.expanduser(yosemite_icloud_path)

    if not os.path.isdir(icloud_home):
        error(constants.ERROR_UNABLE_TO_FIND_STORAGE.format(provider="iCloud Drive"))

    return str(icloud_home)


def is_process_running(process_name: str) -> bool:
    """
    Check if a process with the given name is running.

    Args:
        (str): Process name, e.g. "Sublime Text"

    Returns:
        (bool): True if the process is running
    """
    is_running: bool = False

    # On systems with pgrep, check if the given process is running
    if os.path.isfile("/usr/bin/pgrep"):
        dev_null = open(os.devnull, "wb")
        returncode: int = subprocess.call(["/usr/bin/pgrep", process_name], stdout=dev_null)
        is_running = bool(returncode == 0)

    return is_running


def remove_acl(path: str) -> None:
    """
    Remove the ACL of the file or folder located on the given path.

    Also remove the ACL of any file and folder below the given one,
    recursively.

    Args:
        path (str): Path to the file or folder to remove the ACL for,
                    recursively.
    """
    # Some files have ACLs, let's remove them recursively
    if platform.system() == constants.PLATFORM_DARWIN and os.path.isfile("/bin/chmod"):
        subprocess.call(["/bin/chmod", "-R", "-N", path])
    elif (platform.system() == constants.PLATFORM_LINUX) and os.path.isfile(
        "/bin/setfacl"
    ):
        subprocess.call(["/bin/setfacl", "-R", "-b", path])


def remove_immutable_attribute(path: str) -> None:
    """
    Remove the immutable attribute of the given path.

    Remove the immutable attribute of the file or folder located on the given
    path. Also remove the immutable attribute of any file and folder below the
    given one, recursively.

    Args:
        path (str): Path to the file or folder to remove the immutable
                    attribute for, recursively.
    """
    # Some files have ACLs, let's remove them recursively
    if (platform.system() == constants.PLATFORM_DARWIN) and os.path.isfile(
        "/usr/bin/chflags"
    ):
        subprocess.call(["/usr/bin/chflags", "-R", "nouchg", path])
    elif platform.system() == constants.PLATFORM_LINUX and os.path.isfile(
        "/usr/bin/chattr"
    ):
        subprocess.call(["/usr/bin/chattr", "-R", "-f", "-i", path])


def can_file_be_synced_on_current_platform(path: str) -> bool:
    """
    Check if the given path can be synced locally.

    Check if it makes sense to sync the file at the given path on the current
    platform.
    For now we don't sync any file in the ~/Library folder on GNU/Linux.
    There might be other exceptions in the future.

    Args:
        (str): Path to the file or folder to check. If relative, prepend it
               with the home folder.
               'abc' becomes '~/abc'
               '/def' stays '/def'

    Returns:
        (bool): True if given file can be synced
    """
    can_be_synced: bool = True

    # If the given path is relative, prepend home
    fullpath: str = os.path.join(os.environ["HOME"], path)

    # Compute the ~/Library path on macOS
    # End it with a slash because we are looking for this specific folder and
    # not any file/folder named LibrarySomething
    library_path: str = os.path.join(os.environ["HOME"], "Library/")

    if platform.system() == constants.PLATFORM_LINUX:
        if fullpath.startswith(library_path):
            can_be_synced = False

    return can_be_synced


def detect_path_type(path: str) -> str:
    """
    Detect the normalized type for a path.

    Returns:
        str: file, dir, link, or missing
    """
    if os.path.isfile(path):
        return "file"
    if os.path.isdir(path):
        return "dir"
    if os.path.islink(path):
        return "link"
    return "missing"


def normalize_managed_path(path: str) -> str:
    """
    Normalize a managed relative path before filesystem operations.

    Directory entries in app configs may end with a trailing slash. Strip it so
    joins, symlink creation, and staged comparisons operate on the real path.
    """
    normalized = path.rstrip("/\\")
    return normalized or path


def files_are_identical(left: str, right: str) -> bool:
    """
    Compare two files by content.

    Returns:
        bool: True when file contents match
    """
    return filecmp.cmp(left, right, shallow=False)


def directories_are_identical(left: str, right: str) -> bool:
    """
    Recursively compare two directories by contents.

    Returns:
        bool: True when directory trees match
    """
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False

    (_, mismatches, errors) = filecmp.cmpfiles(
        left, right, comparison.common_files, shallow=False
    )
    if mismatches or errors:
        return False

    for dirname in comparison.common_dirs:
        if not directories_are_identical(
            os.path.join(left, dirname), os.path.join(right, dirname)
        ):
            return False

    return True


def get_diff_status(local_path: str, backup_path: str) -> str:
    """
    Derive a stable diff status for one managed path.

    Returns:
        str
    """
    local_type = detect_path_type(local_path)
    backup_type = detect_path_type(backup_path)

    if local_type == "missing" and backup_type == "missing":
        return "both_missing"
    if local_type == "missing":
        return "missing_local"
    if backup_type == "missing":
        return "missing_backup"

    if os.path.islink(local_path) and os.path.exists(backup_path):
        try:
            if os.path.samefile(local_path, backup_path):
                return "linked_to_backup"
        except FileNotFoundError:
            pass

    if local_type != backup_type:
        return "different"
    if local_type == "file":
        return "identical" if files_are_identical(local_path, backup_path) else "different"
    if local_type == "dir":
        return (
            "identical"
            if directories_are_identical(local_path, backup_path)
            else "different"
        )

    return "different"


def get_diff_display_type(local_path: str, backup_path: str) -> str:
    """
    Determine the type to show in diff output.

    Returns:
        str
    """
    local_type = detect_path_type(local_path)
    if local_type != "missing":
        return local_type

    backup_type = detect_path_type(backup_path)
    if backup_type != "missing":
        return backup_type

    return "missing"


def render_table(headers: Sequence[str], rows: Sequence[Dict[str, str]]) -> str:
    """
    Render a simple ASCII table.

    Returns:
        str
    """
    string_rows: List[Dict[str, str]] = [
        {header: str(row.get(header, "")) for header in headers} for row in rows
    ]
    widths = {
        header: max(
            len(header), *(len(row[header]) for row in string_rows)
        )
        for header in headers
    }

    def render_row(row: Dict[str, str]) -> str:
        return " | ".join(row[header].ljust(widths[header]) for header in headers)

    separator = "-+-".join("-" * widths[header] for header in headers)
    header_row = render_row({header: header for header in headers})
    body = [render_row(row) for row in string_rows]

    return "\n".join([header_row, separator, *body])


def resolve_backup_root(default_root: str, override_root: Optional[str] = None) -> str:
    """
    Resolve the backup root used for comparisons and bcomp.

    Returns:
        str
    """
    resolved_root = override_root or default_root
    resolved_root = os.path.expanduser(resolved_root)
    if not os.path.isabs(resolved_root):
        resolved_root = os.path.join(os.environ["HOME"], resolved_root)
    return resolved_root


def run_bcomp_on_rows(
    rows: Sequence[Dict[str, str]],
    local_root: str,
    backup_root: str,
    dry_run: bool,
    verbose: bool,
) -> None:
    """
    Launch one bcomp process for a collection of managed paths.
    """
    left_stage = tempfile.mkdtemp(
        prefix=".mackup_bcomp_local_", dir=_stage_parent_for_root(local_root)
    )
    right_stage = tempfile.mkdtemp(
        prefix=".mackup_bcomp_backup_", dir=_stage_parent_for_root(backup_root)
    )

    try:
        seen_paths = set()
        for row in rows:
            relative_path = normalize_managed_path(row["Path"])
            if relative_path in seen_paths:
                continue
            seen_paths.add(relative_path)

            source_local = os.path.join(local_root, relative_path)
            source_backup = os.path.join(backup_root, relative_path)
            staged_local = os.path.join(left_stage, relative_path)
            staged_backup = os.path.join(right_stage, relative_path)

            if detect_path_type(source_local) != "missing":
                materialize_editable_stage(source_local, staged_local)
            if detect_path_type(source_backup) != "missing":
                materialize_editable_stage(source_backup, staged_backup)

        command = "bcomp {} {}".format(
            _shell_quote(left_stage), _shell_quote(right_stage)
        )
        if verbose or dry_run:
            print(command)
        if not dry_run:
            subprocess.run(["bash", "-lc", command], check=False)
    finally:
        shutil.rmtree(left_stage)
        shutil.rmtree(right_stage)


def _shell_quote(path: str) -> str:
    """Return a shell-safe single-quoted path."""
    return "'" + path.replace("'", "'\"'\"'") + "'"


def _stage_parent_for_root(root: str) -> str:
    """
    Pick a writable parent on the same filesystem as a source root.
    """
    resolved_root = os.path.abspath(root)
    if os.path.isdir(resolved_root):
        return resolved_root
    return os.path.dirname(resolved_root)


def materialize_editable_stage(source: str, staged: str) -> None:
    """
    Materialize a source path into an editable bcomp staging tree.

    Files are staged as hard links so edits propagate to the original file.
    Directories are recreated as real directories and their files are staged as
    hard links recursively.
    """
    source_type = detect_path_type(source)
    if source_type == "file":
        _hardlink_file(source, staged)
        return

    if source_type == "dir":
        os.makedirs(staged, exist_ok=True)
        for root, dirs, files in os.walk(source):
            rel_root = os.path.relpath(root, source)
            staged_root = staged if rel_root == "." else os.path.join(staged, rel_root)
            os.makedirs(staged_root, exist_ok=True)
            for directory in dirs:
                os.makedirs(os.path.join(staged_root, directory), exist_ok=True)
            for filename in files:
                _hardlink_file(
                    os.path.join(root, filename), os.path.join(staged_root, filename)
                )
        return

    raise ValueError("Unsupported file for editable bcomp staging: {}".format(source))


def _hardlink_file(source: str, staged: str) -> None:
    """
    Stage one file as a hard link.
    """
    parent = os.path.dirname(os.path.abspath(staged))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    os.link(source, staged)
