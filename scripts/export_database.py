"""Export the configured database as a portable PostgreSQL archive."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New .dump file to create")
    args = parser.parse_args()
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        parser.error("Install PostgreSQL client tools (same major version as the server or newer).")
    output = args.output.resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    url = make_url(get_settings().database_url).set(drivername="postgresql")
    env = os.environ.copy()
    env["PGCONNECT_TIMEOUT"] = "10"
    if url.password is not None:
        env["PGPASSWORD"] = url.password
    # Keep the password out of command arguments and diagnostic output.
    connection = url.set(password=None).render_as_string(hide_password=False)
    fd, temporary = tempfile.mkstemp(dir=output.parent, suffix=".dump.partial")
    os.close(fd)
    try:
        subprocess.run(
            [pg_dump, "--dbname", connection, "--format=custom", "--no-owner",
             "--no-privileges", "--file", temporary],
            env=env,
            check=True,
        )
        # Publish only complete archives, without overwriting another export.
        os.link(temporary, output)
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Export failed ({type(exc).__name__}); no archive published.", file=sys.stderr)
        return 1
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f"Export created: {output} ({output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
